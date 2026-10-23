# 设计决策记录

格式：**决策 / 备选方案 / 为什么这样选**

---

## 阶段 0

### D1. 配置用惰性单例 `@lru_cache get_settings()`，而不是模块级 `settings = Settings()`

- **决策**：`app/core/config.py` 暴露 `@lru_cache def get_settings() -> Settings`
- **备选**：模块级 `settings = Settings()`，import 时即实例化
- **为什么**：
  - 模块级写法在 **import 的瞬间**就实例化，测试里来不及用 `monkeypatch.setenv` 改环境变量；惰性写法在第一次调用时才读配置，测试可控
  - `lru_cache` 自带 `cache_clear()`，测试之间能重置；模块级要靠 `importlib.reload()`，很脏
  - 配合 FastAPI 的 `Depends(get_settings)`，测试可用 `dependency_overrides` 一行替换
- **代价与补救**：惰性写法丢掉了启动时的 fail-fast。在 `main.py` 模块级主动调一次 `get_settings()` 补回来——"惰性 + 一次显式触发"，两边好处都拿到

### D2. 配置优先级：真实环境变量 > `.env` 文件 > 代码默认值

- **决策**：用 `pydantic-settings` 的默认优先级，不改
- **备选**：只读 `.env`；或散落的 `os.getenv()`
- **为什么**：生产环境没有 `.env` 文件，密钥由 K8s Secret / AWS Secrets Manager 注入成环境变量。环境变量优先级最高，同一份代码本地读文件、线上读注入值，不改一行代码
- **相关**：密钥只进 `.env`（已 gitignore），仓库里只放 `.env.example` 作为"需要哪些变量"的清单

### D3. 开启 `validate_default=True`

- **决策**：在 `SettingsConfigDict` 里打开
- **为什么**：pydantic v2 默认不校验默认值。曾写出 `app_env: str = "local",`（行尾多一个逗号），默认值实际是元组 `("local",)` 而 pydantic 静默接受，之后 `== "local"` 永远为 False 且无任何报错。打开后这类错误在启动时就暴露

### D4. 目录按层分：`api/` / `core/`，依赖单向

- **决策**：`api/routes/` 只做 HTTP 层，`core/` 放配置等基础设施；`api` 可依赖 `core`，反之不可
- **备选**：按功能平铺，或全部写在 `main.py`
- **为什么**：阶段 4 的评估脚本要绕过 HTTP 直接 import `rag` 模块来跑。检索逻辑若写在路由函数里，就只能靠发 HTTP 请求来测，慢且难调试

### D5. 不用高层框架（LangChain / LlamaIndex），阶段 0–4 全手写

- **决策**：核心逻辑手写，阶段 5 最后才引入 LangGraph 做对照
- **为什么**：项目目的是搞懂原理以准备面试，不是最快做出产品。框架会把切分、检索、Agent 循环这些关键决策藏起来，而这些恰好是面试要问的

## 阶段 2

### D6. 上下文策略做成可配置，默认 truncate

- **决策**：`context_strategy` 配置项，`truncate` / `summarize` 两种实现，默认 truncate
- **为什么**：实测（`scripts/compare_context.py`）1429 token 的历史压到 400 预算下——
  truncate 丢掉最早的轮次，模型答不出早期信息；summarize 多花一次 LLM 调用（约 $0.00022），
  但保住了关键事实。每轮省约 900 输入 token（$0.00009），**约 2.5 轮回本**
- **代价**：摘要是有损压缩，细节（"第 3 次问的是什么"）仍然丢失

### D7. 结构化输出用「schema 塞进 system + 校验失败把错误发回去」

- **决策**：`app/llm/structured.py`，把 Pydantic 的 JSON Schema 放进 system prompt，
  解析失败时把模型的错误输出和校验报错一起作为新一轮消息发回去让它改正，次数用尽走 fallback
- **备选**：直接 `json.loads` 不重试；或用厂商的 structured output 参数
- **为什么**：不重试的话偶发的格式问题会直接变成 500；厂商参数各家不同，会污染统一接口。
  把错误反馈回去让模型自纠，是跨厂商通用的做法
- **应用**：新对话的标题自动生成走的就是这条路径，带 fallback（取用户首句前 12 字）

## 阶段 3

### D8. 向量和业务数据都放 PostgreSQL（pgvector），不单独部署向量库

- **决策**：`documents` / `chunks` 两张表，向量是 `vector(1024)` 列
- **备选**：Pinecone / Milvus / Qdrant
- **为什么**：文档内容、元数据、向量一条 SQL 查得出来，不用在两个系统间同步，
  也不会出现"向量库里有但业务库已删除"的不一致。数据量小时性能完全够
- **代价**：超大规模（亿级向量）时专用向量库更强

### D9. `documents` 表记录切分策略与 embedding 模型

- **决策**：存 `strategy` / `chunk_size` / `embedding_model` / `embedding_dim`
- **为什么**：阶段 4 要对比不同切分策略的检索效果，没有这些字段就分不清库里
  哪批 chunk 是什么配置生成的。换 embedding 模型后旧向量在不同语义空间，
  必须能识别出来。和 D1 的 `prompt_version` 是同一类问题：**配置要能追溯**

### D10. 先手写 NumPy 暴力检索，不直接用 pgvector 的 `<=>`

- **决策**：`app/rag/retrieval.py` 手写余弦相似度 + 暴力扫描
- **验证**：对同一问题，手写结果和 `<=>` 的距离完全一致（0.4456 / 0.4937 / 0.4965）
- **实测性能**（1 万条 × 1024 维）：
  - NumPy 全向量化 13ms
  - Python 循环 + NumPy 逐行计算 18ms
  - 纯 Python 407ms（**比 NumPy 慢 32 倍**）
- **结论**：慢的不是"循环"这个结构，而是让 Python 解释器做大量逐个数字的运算。
  NumPy 的价值在于把计算交给底层 BLAS，不只是消除循环
- **另一个发现**：bge-m3 输出已归一化（模长 = 1），所以余弦退化成纯点积——
  这正是 pgvector 提供 `<#>`（负内积）的原因。代码里保留除法是为了换模型时仍正确
