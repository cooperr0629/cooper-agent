from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import chat, health
from app.core.config import get_settings
from app.core.db import close_pool, init_pool
from app.llm.client import close_client, init_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # yield 之前：启动时跑一次。配置有问题就在这里挂掉，而不是等第一个请求
    settings = get_settings()
    await init_pool(settings.database_url)
    init_client(settings.anthropic_api_key, settings.anthropic_model)

    yield  # 应用在这里服务

    # yield 之后：关闭时跑一次，顺序和获取时相反
    await close_client()
    await close_pool()


app = FastAPI(title="知识库问答助手", lifespan=lifespan)

app.include_router(health.router)
app.include_router(chat.router)
