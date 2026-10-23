"""检索。先手写暴力扫描，搞懂 pgvector 的 <=> 底下在算什么。"""

from typing import Any
from uuid import UUID

import numpy as np

from app.core.db import get_pool


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """两个一维向量的余弦相似度 = 点积 / (模长a × 模长b)。

    除以模长是为了消掉「长度」的影响，只比较方向——
    文本向量的长度没有语义，有意义的只有方向。
    """
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def brute_force_search(
    query_vec: np.ndarray,  # shape (D,)
    chunk_matrix: np.ndarray,  # shape (N, D)
    top_k: int = 5,
) -> list[tuple[int, float]]:
    """和每个 chunk 算一遍相似度，返回 [(下标, 相似度), ...] 降序前 top_k。"""
    # (N, D) @ (D,) → (N,)：一次算出 N 个点积，不用循环
    dots = chunk_matrix @ query_vec
    # axis=1 = 沿每一行算，得到 N 个模长
    norms = np.linalg.norm(chunk_matrix, axis=1)
    # 两个 (N,) 数组逐元素相除（广播）
    sims = dots / (norms * np.linalg.norm(query_vec))

    # argsort 升序 → [::-1] 反转成降序 → 取前 k 个下标
    idx = np.argsort(sims)[::-1][:top_k]
    # 转回 Python 原生类型，否则存库或转 JSON 会出问题
    return [(int(i), float(sims[i])) for i in idx]


def brute_force_search_slow(
    query_vec: np.ndarray, chunk_matrix: np.ndarray, top_k: int = 5
) -> list[tuple[int, float]]:
    """同样的逻辑，用 Python 循环写。只用来对比速度。"""
    sims = [(i, cosine_similarity(query_vec, row)) for i, row in enumerate(chunk_matrix)]
    sims.sort(key=lambda x: x[1], reverse=True)
    return sims[:top_k]


def parse_pgvector(s: str) -> np.ndarray:
    """pgvector 转成文本后是 '[0.1,0.2,...]'，解析成 numpy 数组。"""
    return np.fromstring(s.strip("[]"), sep=",")


async def load_chunk_matrix(
    document_id: UUID | None = None,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """把 chunk 的向量读成一个 (N, D) 矩阵，连同元信息一起返回。

    矩阵的第 i 行，对应元信息列表的第 i 项 —— 下标一一对应，这是后面能用
    「下标」定位 chunk 的前提。
    """
    sql = "SELECT id, text, heading, embedding::text AS emb FROM chunks"
    args = []
    if document_id is not None:
        sql += " WHERE document_id = $1"
        args.append(document_id)
    sql += " ORDER BY id"

    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *args)

    matrix = np.vstack([parse_pgvector(r["emb"]) for r in rows])
    meta = [{"id": r["id"], "text": r["text"], "heading": r["heading"]} for r in rows]
    return matrix, meta
