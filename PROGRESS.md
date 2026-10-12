# PROGRESS

> 每次会话开始先读这个文件，结束前更新。

## 当前状态

- **当前阶段**：阶段 0（项目骨架）
- **开始日期**：2026-10-12
- **项目状态**：空目录，只有 CLAUDE.md

## 阶段 0 待办

- [ ] 环境：创建 conda 环境 `kb-agent`，Python 3.11+（当前 base 是 3.10.9，不满足）
- [ ] 环境：安装 Docker Desktop（阶段 0 起 PostgreSQL 跑在容器里，阶段 8 要 docker compose）
- [ ] `git init` + `.gitignore`（必须含 `.env`）
- [ ] 目录结构与 `pyproject.toml`
- [ ] 配置管理：`app/core/config.py`，用 pydantic-settings 从 `.env` 读取
- [ ] FastAPI 启动，`GET /health` 返回 200
- [ ] docker-compose 起 pgvector 镜像的 PostgreSQL
- [ ] `/health` 里真实检测数据库连通性（asyncpg）
- [ ] 面试自测：事件循环是什么？同步代码放进 async 函数会发生什么？

## 已完成

（暂无）

## 没掌握 / 答错过的问题

（暂无）

## 下一步

先搭好 Python 3.11 环境和 Docker，再动手写 config 和 /health。
