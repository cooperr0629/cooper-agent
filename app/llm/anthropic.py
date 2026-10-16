import asyncio
import json
import logging
import random
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.llm.base import ChatResponse, Usage

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

logger = logging.getLogger(__name__)


class AnthropicClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._model = model
        self._max_retries = max_retries
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

        t0 = time.perf_counter()

        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._client.post(API_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
                usage = Usage(
                    input_tokens=data["usage"]["input_tokens"],
                    output_tokens=data["usage"]["output_tokens"],
                )
                logger.info(
                    "chat_model=%s in=%d out=%d elapsed=%.0fms retries=%d",
                    data["model"],
                    usage.input_tokens,
                    usage.output_tokens,
                    (time.perf_counter() - t0) * 1000,
                    attempt,
                )
                return ChatResponse(
                    result=text,
                    usage=usage,
                    model=data["model"],
                    stop_reason=data["stop_reason"],
                    raw=data,
                )
            except httpx.HTTPStatusError as e:
                code = e.response.status_code
                if code != 429 and code < 500:
                    raise  # 4xx：请求本身有问题，重试也没用
                if attempt == self._max_retries:
                    raise
                delay = self._backoff(attempt, e.response.headers.get("retry-after"))
                logger.warning("HTTP %d, %.1fs 后重试(第 %d 次)", code, delay, attempt + 1)
                await asyncio.sleep(delay)

            except httpx.TransportError as e:
                if attempt == self._max_retries:
                    raise
                delay = self._backoff(attempt, None)
                logger.warning(
                    "网络错误 %s, %.1fs 后重试(第%d 次)", type(e).__name__, delay, attempt + 1
                )
                await asyncio.sleep(delay)

        raise RuntimeError("unreachable")

    @staticmethod
    def _backoff(attempt: int, retry_after: str | None) -> float:
        if retry_after:
            return float(retry_after)
        return min(2**attempt + random.uniform(0, 1), 60.0)

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
