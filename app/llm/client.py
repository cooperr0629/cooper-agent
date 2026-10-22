from app.llm.anthropic import AnthropicClient
from app.llm.base import LLMClient

_client: LLMClient | None = None


def init_client(api_key: str, model: str) -> None:
    global _client
    _client = AnthropicClient(api_key=api_key, model=model)


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_client() -> LLMClient:
    if _client is None:
        raise RuntimeError("LLM客户端未初始化")
    return _client
