import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.llm.base import ChatResponse, Usage

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


class AnthropicClient:
    def __init__(self, api_key: str, model: str, timeout: float = 30.0) -> None:
        self._model = model
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "x-api-key": api_key,
                "anthropic-version": API_VERSION,
                "content-type": "application/json",
            },
        )

    async def chat(  # 模型整段返回
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system is not None:
            payload["system"] = system
        payload.update(kwargs)
        resp = await self._client.post(API_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        text = "".join(b["text"] for b in data["content"] if b["type"] == "text")

        return ChatResponse(
            result=text,
            usage=Usage(
                input_tokens=data["usage"]["input_tokens"],
                output_tokens=data["usage"]["output_tokens"],
            ),
            model=data["model"],
            stop_reason=data["stop_reason"],
            raw=data,
        )

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": messages,
            "stream": True,
        }
        if system is not None:
            payload["system"] = system
        payload.update(kwargs)
        async with self._client.stream("POST", API_URL, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                if event["type"] == "content_block_delta":
                    yield event["delta"]["text"]

    async def aclose(self) -> None:
        await self._client.aclose()
