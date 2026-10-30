# PROGRESS

> 每次会话开始先读这个文件，结束前更新。

## 当前状态

- **当前阶段**：阶段 3（RAG）
- **开始日期**：2026-10-12
- **项目状态**：FastAPI 服务可运行，`GET /health` 返回 `{"status":"ok","env":"local"}`

## 阶段 0 待办（已全部完成）

- [x] 环境：conda 环境 `kb-agent`，Python 3.11.17
- [x] 环境：Docker 已安装（29.8.2）
- [x] `git init` + `.gitignore`（必须含 `.env`）
- [x] 目录结构与 `pyproject.toml`
- [x] 配置管理：`app/core/config.py`，惰性单例 `get_settings()`
- [x] FastAPI 启动，`GET /health` 返回 200
- [x] docker-compose 起 pgvector 镜像的 PostgreSQL
- [x] `/health` 里真实检测数据库连通性（asyncpg），降级路径已验证
- [x] 概念过关：事件循环、同步代码放进 async 函数的后果（讲解时已覆盖）

## 已完成

- 2026-10-12 `git init -b main`，写好 `.gitignore`（已验证 `.env` 被忽略），完成首个 commit `8858c6c`。远端 `origin` 与 push 待自己操作。

## 没掌握 / 答错过的问题

- **2026-10-30｜HNSW 的 m 调大有什么影响？** 结论答对了，但原因说成"高速公路变多"。纠正：m 是每个节点的邻居上限（路口有几条岔路），不是上层节点变多。同一个 ef_search 下 m 大更慢，但要在同一 recall 下比较。
- **2026-10-30｜ef_search=5 但 LIMIT 10 会怎样？** 跳过了，做完 ⑤ 的实验后再答。
- **2026-10-30｜待答**：rst 的 `levels` 改成全局字典有什么影响？查询换 nomic-embed-text、库不动会出什么问题？

- **2026-10-12｜密钥误提交后还安不安全？** 没答出来。要点：commit 是不可变快照，`clone` 默认拉全部历史，所以删文件 + 补 `.gitignore` 对历史无效，`git show <旧commit>:.env` 照样能读出来。唯一可靠处置是**立刻吊销并轮换密钥**；改写历史（filter-repo / BFG）是补充，不是解法。阶段 8 讲安全时再复盘一次。

## 阶段 1（LLM 接入层）已完成

- [x] 不用 SDK，httpx 直发原始请求：`scripts/raw_call.py`，看清了 content 块数组、usage、stop_reason
- [x] `LLMClient` 接口（Protocol）+ `Usage` / `ChatResponse` 数据类：`app/llm/base.py`
- [x] `AnthropicClient.chat()`：`app/llm/anthropic.py`，真实调用通过
- [x] 模型可配置：`.env` 的 `ANTHROPIC_MODEL`，默认 `claude-haiku-5-5`（比 Opus 便宜 40 倍）
- [x] `AnthropicClient.stream()`：SSE 流式输出，首字延迟 1.0s vs 非流式 1.6s
- [~] 第二家厂商：**跳过 DeepSeek**（要单独充值，且有涨价公告）。改为阶段 6 用 Ollama 做——同样是 OpenAI 兼容格式，对抽象层的检验效果一样，且免费
- [x] 超时、重试（指数退避 + 抖动）、Token 用量与耗时日志。实测：404 立刻失败不重试，503 重试 3 次间隔 1.8/2.7/4.8s

### 阶段 2 已完成

- [x] 建表：`conversations` / `messages`（`migrations/001_init.sql`）
- [x] asyncpg 连接池 + FastAPI lifespan（技术债已还）。实测 30 并发只占 10 条连接，耗时 0.04s
- [x] `/chat` 接口接上 LLMClient，多轮对话能记住上下文（实测第二轮答出第一轮说的名字）
- [x] 上下文过长：`app/llm/context.py` 的 truncate / summarize，可配置。对比见 `scripts/compare_context.py`
- [x] 结构化输出：`app/llm/structured.py`，schema 进 system + 校验失败回喂错误 + fallback。用于自动生成对话标题

### 阶段 3（RAG）进行中

- [x] ① 文档解析：`app/rag/loader.py`（Markdown / txt / PDF）
- [x] ② 两种切分：`app/rag/chunking.py`（固定长度+重叠 / 按标题，标题路径拼进正文）
- [x] ③ Embedding + 入库：本机 Ollama 跑 bge-m3（1024 维），`migrations/002_rag.sql`，
      `app/repositories/documents.py` 的 `ingest()`
- [x] ④ NumPy 手写暴力检索：`app/rag/retrieval.py`，结果与 pgvector `<=>` 完全一致
- [ ] ⑤ HNSW 索引对比。语料：CPython 3.13 文档（`data/cpython-src/Doc`，517 个 .rst，12MB，已 gitignore）
      - [x] loader 支持 .rst（标题转成 Markdown `#`，复用 chunk_by_heading）
      - [x] 批量入库：`scripts/ingest_corpus.py`，19049 个 chunk，14 分钟（已删 10-23 的 5 万条随机向量）
      - [ ] `scripts/bench_hnsw.py`：暴力检索当标准答案 → 建 HNSW → 对比延迟 / Recall@10 / 调 m 和 ef_search ← **当前**
- [ ] ⑥ BM25 关键词检索 → 混合检索
- [ ] ⑦ Rerank
- [ ] ⑧ 回答标注引用来源
- [ ] 然后：阶段 4 评估 → RAPTOR

**环境**：Ollama 已装并常驻，模型 bge-m3（embedding）+ llama3.1 / qwen2.5 / llama3.2（对话，阶段 6 用）

### 已讲过的概念

async/await 的使用时机、异步生成器与 `async for`、Protocol 结构化类型、dataclass、
keyword-only 参数（`*`）、适配器模式、单下划线命名约定、import 路径规则
