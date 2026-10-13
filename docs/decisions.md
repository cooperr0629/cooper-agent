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
