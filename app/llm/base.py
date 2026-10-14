from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Usage:  # 比起pydantic不用校验
    input_tokens: int
    output_tokens: int


@dataclass
class ChatResponse:
    usage: Usage
    result: str
    model: str
    stop_reason: str
    raw: dict = field(default_factory=dict)


class LLMClient(Protocol):
    async def chat(  # 模型整段返回
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ChatResponse: ...

    def stream(  # 模型生成一段返回一段
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncIterator[str]: ...
