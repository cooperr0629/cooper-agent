from fastapi import FastAPI

from app.api.routes import health
from app.core.config import get_settings

app = FastAPI(title="知识库问答助手")

# 启动时主动触发一次配置校验：配置有问题就在这里挂掉，而不是等第一个请求
get_settings()

app.include_router(health.router)
