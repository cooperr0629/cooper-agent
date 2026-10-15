"""不用 SDK，直接用 httpx 调一次 Anthropic Messages API，看清原始请求和响应。"""

import asyncio
import json

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
        "max_tokens": 1024,
        "system": "你是一个简洁的助手，回答控制在两句话以内。",
        "messages": [
            {"role": "user", "content": "用一句话解释什么是向量数据库"},
        ],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(API_URL, headers=headers, json=payload, timeout=30)

    print(f"模型 {settings.anthropic_model} → HTTP {resp.status_code}\n")
    data = resp.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))

    # content 是 block 数组，要遍历找 type == "text" 的块，不能写 content[0]["text"]
    if resp.status_code == 200:
        text = "".join(b.get("text", "") for b in data["content"] if b["type"] == "text")
        usage = data["usage"]
        print(f"\n--- 提取出的回答 ---\n{text}")
        print(
            f"\n--- 用量 ---\n输入 {usage['input_tokens']} token，"
            f"输出 {usage['output_tokens']} token"
        )


if __name__ == "__main__":
    asyncio.run(main())
