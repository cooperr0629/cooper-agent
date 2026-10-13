import asyncpg
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    settings = get_settings()

    conn = None
    try:
        conn = await asyncpg.connect(settings.database_url)
        await conn.fetchval("SELECT 1")
        db_status = "up"
    except Exception:
        db_status = "down"
    finally:
        if conn is not None:
            await conn.close()

    return {
        "status": "ok" if db_status == "up" else "degraded",
        "env": settings.app_env,
        "db": db_status,
    }
