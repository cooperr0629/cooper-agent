"""把一个目录下的文档批量灌进库，给阶段 3 ⑤ 的 HNSW 对比准备几万条数据。

用法：
    python -m scripts.ingest_corpus data/cpython-src/Doc --glob '*.rst'

可以断点续跑：已经入库的文件（按相对路径判断）默认跳过，中途 Ctrl+C 后重跑即可。
"""

import argparse
import asyncio
import logging
import time
from pathlib import Path

from app.core.config import get_settings
from app.core.db import close_pool, get_pool, init_pool
from app.rag.embeddings import OllamaEmbeddingClient
from app.repositories.documents import ingest

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("app.repositories.documents").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def main(root: Path, pattern: str, strategy: str, chunk_size: int, force: bool) -> None:
    s = get_settings()
    await init_pool(s.database_url)
    embedder = OllamaEmbeddingClient(base_url=s.ollama_base_url, model=s.embedding_model)

    files = sorted(root.rglob(pattern))
    async with get_pool().acquire() as conn:
        done = {r["filename"] for r in await conn.fetch("SELECT filename FROM documents")}

    t0 = time.perf_counter()
    skipped = failed = 0
    try:
        for n, f in enumerate(files, 1):
            source = str(f.relative_to(root))
            if source in done and not force:
                skipped += 1
                continue
            try:
                await ingest(
                    f,
                    embedder,
                    strategy=strategy,
                    chunk_size=chunk_size,
                    embedding_model=s.embedding_model,
                    source=source,
                )
            except Exception as e:  # 单个文件失败不该中断整批
                failed += 1
                logger.warning("失败 %s：%s", source, e)
            if n % 20 == 0:
                logger.info("[%d/%d] 已用 %.0fs", n, len(files), time.perf_counter() - t0)
    finally:
        await embedder.aclose()
        async with get_pool().acquire() as conn:
            total = await conn.fetchval("SELECT count(*) FROM chunks")
        await close_pool()

    logger.info(
        "完成：%d 个文件，跳过 %d，失败 %d，库里共 %d 个 chunk，耗时 %.0fs",
        len(files),
        skipped,
        failed,
        total,
        time.perf_counter() - t0,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    p.add_argument("--glob", default="*.rst")
    p.add_argument("--strategy", default="heading", choices=["heading", "fixed"])
    p.add_argument("--chunk-size", type=int, default=800)
    p.add_argument("--force", action="store_true", help="已入库的也重新导入")
    a = p.parse_args()
    asyncio.run(main(a.root, a.glob, a.strategy, a.chunk_size, a.force))
