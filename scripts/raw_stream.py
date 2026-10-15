"""看清 Anthropic 流式响应的原始 SSE 数据。"""

import asyncio

import httpx

from app.core.config import get_settings

API_URL = "https://api.anthropic.com/v1/messages"


async def main() -> None:
    settings = get_settings()

    headers = {
        "x-api-key": settings.anthropic_api_key or "",
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": settings.anthropic_model,
        "max_tokens": 256,
        "stream": True,  # ← 和 raw_call.py 的唯一区别
        "messages": [{"role": "user", "content": "用一句话解释向量数据库"}],
    }

    async with httpx.AsyncClient(timeout=30) as client:
        async with client.stream("POST", API_URL, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():  # ← 一行一行地收
                print(repr(line))


if __name__ == "__main__":
    asyncio.run(main())
