# PROGRESS

> 每次会话开始先读这个文件，结束前更新。

## 当前状态

- **当前阶段**：阶段 2（对话与提示词）
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

- **2026-10-12｜密钥误提交后还安不安全？** 没答出来。要点：commit 是不可变快照，`clone` 默认拉全部历史，所以删文件 + 补 `.gitignore` 对历史无效，`git show <旧commit>:.env` 照样能读出来。唯一可靠处置是**立刻吊销并轮换密钥**；改写历史（filter-repo / BFG）是补充，不是解法。阶段 8 讲安全时再复盘一次。

## 阶段 1（LLM 接入层）已完成

- [x] 不用 SDK，httpx 直发原始请求：`scripts/raw_call.py`，看清了 content 块数组、usage、stop_reason
- [x] `LLMClient` 接口（Protocol）+ `Usage` / `ChatResponse` 数据类：`app/llm/base.py`
- [x] `AnthropicClient.chat()`：`app/llm/anthropic.py`，真实调用通过
- [x] 模型可配置：`.env` 的 `ANTHROPIC_MODEL`，默认 `claude-haiku-5-5`（比 Opus 便宜 40 倍）
- [x] `AnthropicClient.stream()`：SSE 流式输出，首字延迟 1.0s vs 非流式 1.6s
- [~] 第二家厂商：**跳过 DeepSeek**（要单独充值，且有涨价公告）。改为阶段 6 用 Ollama 做——同样是 OpenAI 兼容格式，对抽象层的检验效果一样，且免费
- [x] 超时、重试（指数退避 + 抖动）、Token 用量与耗时日志。实测：404 立刻失败不重试，503 重试 3 次间隔 1.8/2.7/4.8s

### 阶段 2 待办

- [x] 建表：`conversations` / `messages`（`migrations/001_init.sql`）
- [x] asyncpg 连接池 + FastAPI lifespan（技术债已还）。实测 30 并发只占 10 条连接，耗时 0.04s
- [ ] `/chat` 接口接上 LLMClient，多轮对话能记住上下文
- [ ] 上下文过长：截断 + 摘要两种策略，对比代价
- [ ] 结构化输出：让模型稳定返回 JSON，用 Pydantic 校验，失败有重试或兜底

### 已讲过的概念

async/await 的使用时机、异步生成器与 `async for`、Protocol 结构化类型、dataclass、
keyword-only 参数（`*`）、适配器模式、单下划线命名约定、import 路径规则
