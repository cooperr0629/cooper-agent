"""数据库连接池。整个应用共用一个池，启动时建、关闭时释放。"""

import asyncpg

_pool: asyncpg.Pool | None = None


async def init_pool(dsn: str) -> None:
    """应用启动时调用一次。"""
    global _pool
    _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)


async def close_pool() -> None:
    """应用关闭时调用一次。"""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """给业务代码用。没初始化就报错，不要返回 None 让它在远处炸。"""
    if _pool is None:
        raise RuntimeError("连接池未初始化：init_pool() 没被调用")
    return _pool
