"""文档入库：读文件 → 切分 → 向量化 → 存。只管数据库和编排，不碰 HTTP。"""

import logging
import time
from pathlib import Path
from uuid import UUID

from app.core.db import get_pool
from app.rag.chunking import Chunk, chunk_by_heading, chunk_fixed_all
from app.rag.embeddings import EmbeddingClient
from app.rag.loader import load

logger = logging.getLogger(__name__)

INSERT_CHUNK = """
INSERT INTO chunks (document_id, chunk_index, text, heading, embedding)
VALUES ($1, $2, $3, $4, $5::vector)
"""


def to_pgvector(vec: list[float]) -> str:
    """asyncpg 不认识 vector 类型，转成 '[0.1,0.2,...]' 让 SQL 里的 ::vector 去解析。"""
    return "[" + ",".join(map(str, vec)) + "]"


def split(text: str, source: str, strategy: str, chunk_size: int) -> list[Chunk]:
    if strategy == "heading":
        return chunk_by_heading(text, source, max_size=chunk_size)
    if strategy == "fixed":
        return chunk_fixed_all(text, source, size=chunk_size)
    raise ValueError(f"未知的切分策略 {strategy!r}，可选 'heading' / 'fixed'")


async def ingest(
    path: str | Path,
    embedder: EmbeddingClient,
    *,
    strategy: str = "heading",
    chunk_size: int = 800,
    embedding_model: str = "bge-m3",
    replace: bool = True,
    source: str | None = None,
) -> UUID:
    """把一个文件灌进库，返回 document_id。

    replace=True：同名文件先删后插（CASCADE 会连带删掉旧 chunk）。
    这个默认值是为了你反复调切分参数重导——否则库里会堆一堆重复内容，
    检索时同一段话出现好几次。

    source：存进库里的文档名，默认是文件名。批量导入目录时传相对路径——
    不同目录下常有同名文件（index.rst），只用文件名会被 replace 互相覆盖。
    """
    path = Path(path)
    filename = source or path.name

    # 前三步不需要数据库连接，别占着连接干几秒钟的活（向量化是最慢的一环）
    text = load(path)
    chunks = split(text, filename, strategy, chunk_size)

    t0 = time.perf_counter()
    vectors = await embedder.embed([c.text for c in chunks])
    embed_ms = (time.perf_counter() - t0) * 1000

    if len(vectors) != len(chunks):
        raise RuntimeError(f"向量数 {len(vectors)} 与 chunk 数 {len(chunks)} 不符")
    dim = len(vectors[0])

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():  # 要么全成功，要么全回滚
            if replace:
                await conn.execute("DELETE FROM documents WHERE filename = $1", filename)

            doc_id = await conn.fetchval(
                """
                INSERT INTO documents
                    (filename, strategy, chunk_size, embedding_model, embedding_dim)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                filename,
                strategy,
                chunk_size,
                embedding_model,
                dim,
            )
            await conn.executemany(
                INSERT_CHUNK,
                [
                    (doc_id, c.index, c.text, c.heading, to_pgvector(v))
                    for c, v in zip(chunks, vectors, strict=True)
                ],
            )

    logger.info(
        "入库 %s：%d 块，策略=%s，向量化耗时 %.0fms",
        filename,
        len(chunks),
        strategy,
        embed_ms,
    )
    return doc_id


async def count_chunks(document_id: UUID) -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT count(*) FROM chunks WHERE document_id = $1", document_id
        )
