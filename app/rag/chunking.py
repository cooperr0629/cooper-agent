"""两种切分策略。

chunk 切得好不好，决定了整个 RAG 的上限——切坏了，后面 embedding、
检索、rerank 再怎么优化都救不回来。
"""

import re
from dataclasses import dataclass

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class Chunk:
    text: str
    source: str
    index: int
    heading: str | None = None


def chunk_fixed(text: str, source: str, *, size: int = 500, overlap: int = 80) -> list[str]:
    """按固定长度切，相邻块重叠 overlap 个字符。返回纯文本列表。"""
    if overlap >= size:
        raise ValueError(f"overlap({overlap}) 必须小于 size({size})，否则游标不前进")

    pieces = []
    start = 0
    while start < len(text):
        piece = text[start : start + size].strip()
        if piece:
            pieces.append(piece)
        start += size - overlap
    return pieces


def split_sections(text: str) -> list[tuple[str | None, str]]:
    """按 Markdown 标题把文档切成若干节，返回 [(标题路径, 正文), ...]。"""
    sections = []
    stack: list[tuple[int, str]] = []  # [(层级, 标题)]
    heading: str | None = None
    buf: list[str] = []

    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if not m:
            buf.append(line)
            continue

        sections.append((heading, "\n".join(buf)))  # 存上一节
        buf = []

        level, title = len(m.group(1)), m.group(2).strip()
        while stack and stack[-1][0] >= level:  # 弹掉同级和更深的
            stack.pop()
        stack.append((level, title))
        heading = " > ".join(t for _, t in stack)

    sections.append((heading, "\n".join(buf)))
    return sections


def chunk_by_heading(
    text: str, source: str, *, max_size: int = 800, overlap: int = 80
) -> list[Chunk]:
    """按标题切，每块语义完整。太大的节再用 chunk_fixed 切开。

    标题路径会拼在正文前面：这样 chunk 自己就说明了"我属于哪一节"，
    embedding 的语义更准确（contextual retrieval）。
    """
    chunks: list[Chunk] = []

    for heading, body in split_sections(text):
        body = body.strip()
        if not body:
            continue

        prefix = f"{heading}\n\n" if heading else ""
        if len(prefix + body) <= max_size:
            pieces = [body]
        else:
            pieces = chunk_fixed(body, source, size=max_size, overlap=overlap)

        for p in pieces:
            chunks.append(Chunk(prefix + p, source, len(chunks), heading))

    return chunks


def chunk_fixed_all(text: str, source: str, *, size: int = 500, overlap: int = 80) -> list[Chunk]:
    """纯固定长度切分，不看结构。用来和 chunk_by_heading 做对照。"""
    return [
        Chunk(p, source, i)
        for i, p in enumerate(chunk_fixed(text, source, size=size, overlap=overlap))
    ]
