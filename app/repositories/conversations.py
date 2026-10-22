"""对话与消息的存取。只管数据库，不碰 HTTP。"""

import json
from typing import Any
from uuid import UUID

from app.core.db import get_pool


async def create_conversation(title: str | None = None, prompt_version: str = "v1") -> UUID:
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO conversations (title, prompt_version)
            VALUES ($1, $2)
            RETURNING id
            """,
            title,
            prompt_version,
        )


async def list_messages(conversation_id: UUID) -> list[dict[str, str]]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT role, content
            FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at, id
            """,
            conversation_id,
        )
    return [{"role": r["role"], "content": r["content"]} for r in rows]


async def add_message(
    conversation_id: UUID,
    role: str,
    content: str,
    usage: dict[str, Any] | None = None,
) -> None:
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, usage)
            VALUES ($1, $2, $3, $4)
            """,
            conversation_id,
            role,
            content,
            json.dumps(usage) if usage is not None else None,
        )


async def set_title(conversation_id: UUID, title: str) -> None:
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE conversations SET title = $2 WHERE id = $1",
            conversation_id,
            title,
        )
