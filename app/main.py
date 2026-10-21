from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health
from app.core.config import get_settings
from app.core.db import close_pool, init_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    # yield 之前：启动时跑一次
    settings = get_settings()  # 配置有问题就在这里挂掉，而不是等第一个请求
    await init_pool(settings.database_url)

    yield  # 应用在这里服务

    # yield 之后：关闭时跑一次
    await close_pool()


app = FastAPI(title="知识库问答助手", lifespan=lifespan)

app.include_router(health.router)
