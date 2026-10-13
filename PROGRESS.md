# PROGRESS

> 每次会话开始先读这个文件，结束前更新。

## 当前状态

- **当前阶段**：阶段 0（项目骨架）
- **开始日期**：2026-10-12
- **项目状态**：FastAPI 服务可运行，`GET /health` 返回 `{"status":"ok","env":"local"}`

## 阶段 0 待办

- [x] 环境：conda 环境 `kb-agent`，Python 3.11.17
- [x] 环境：Docker 已安装（29.8.2）
- [x] `git init` + `.gitignore`（必须含 `.env`）
- [x] 目录结构与 `pyproject.toml`
- [x] 配置管理：`app/core/config.py`，惰性单例 `get_settings()`
- [x] FastAPI 启动，`GET /health` 返回 200
- [ ] docker-compose 起 pgvector 镜像的 PostgreSQL
- [ ] `/health` 里真实检测数据库连通性（asyncpg）
- [ ] 面试自测：事件循环是什么？同步代码放进 async 函数会发生什么？

## 已完成

- 2026-10-12 `git init -b main`，写好 `.gitignore`（已验证 `.env` 被忽略），完成首个 commit `8858c6c`。远端 `origin` 与 push 待自己操作。

## 没掌握 / 答错过的问题

- **2026-10-12｜密钥误提交后还安不安全？** 没答出来。要点：commit 是不可变快照，`clone` 默认拉全部历史，所以删文件 + 补 `.gitignore` 对历史无效，`git show <旧commit>:.env` 照样能读出来。唯一可靠处置是**立刻吊销并轮换密钥**；改写历史（filter-repo / BFG）是补充，不是解法。阶段 8 讲安全时再复盘一次。

## 下一步

阶段 0 后半段：docker-compose 起 pgvector 版 PostgreSQL，`/health` 用 asyncpg 真实探测数据库连通性。
然后做阶段 0 的面试自测（事件循环、同步代码放进 async 函数）。
