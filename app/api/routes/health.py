from fastapi import APIRouter

from app.core.config import get_settings
from app.core.db import get_pool

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    settings = get_settings()

    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "up"
    except Exception:
        db_status = "down"

    return {
        "status": "ok" if db_status == "up" else "degraded",
        "env": settings.app_env,
        "db": db_status,
    }
