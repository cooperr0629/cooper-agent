"""向量化。

和 LLMClient 分开定义：生成和向量化是两种能力，塞进同一个协议会逼着
Anthropic 的实现去抛 NotImplementedError，接口就脏了。
"""

import logging
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)

# 各模型的输出维度。建表时要用，所以必须是已知常量。
MODEL_DIMS = {
    "bge-m3": 1024,
    "nomic-embed-text": 768,
}


class EmbeddingClient(Protocol):
    """一次传一批文本，返回一批向量，顺序一一对应。

    批量是刻意的：1000 个 chunk 一条条调就是 1000 次网络往返。
    """

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class OllamaEmbeddingClient:
    """本机 Ollama 的 embedding 实现。

    和 AnthropicClient 的区别：
    - 不需要 api key / 版本头，因为是本机服务
    - timeout 要大（CPU 跑得慢），但不需要重试（本机服务没有限流和网络抖动，
      连不上就是没启动，重试没意义）
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "bge-m3",
        timeout: float = 120.0,
        batch_size: int = 32,
    ) -> None:
        self._model = model
        self._batch_size = batch_size
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    @property
    def dim(self) -> int:
        return MODEL_DIMS.get(self._model, 1024)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        # 分批发：一次塞几千条会把本机内存和超时都顶爆
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            payload: dict[str, Any] = {"model": self._model, "input": batch}
            resp = await self._client.post("/api/embed", json=payload)
            resp.raise_for_status()
            vectors.extend(resp.json()["embeddings"])

        if len(vectors) != len(texts):
            raise RuntimeError(f"向量数量({len(vectors)})和文本数量({len(texts)})对不上")
        return vectors

    async def aclose(self) -> None:
        await self._client.aclose()
