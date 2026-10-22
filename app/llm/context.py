"""上下文管理：对话太长时怎么办。

两种策略，代价不同：
- truncate ：直接丢掉最早的消息。快、免费，但模型会彻底忘掉被丢掉的内容
- summarize：把最早的消息压成一段摘要。保住关键信息，但每次压缩要多花一次 LLM 调用，
             而且摘要本身会丢细节（压缩是有损的）
"""

import logging

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)

Messages = list[dict[str, str]]


def estimate_tokens(text: str) -> int:
    """粗估 token 数：ASCII 约 4 字符 1 token，中文约 1 字符 1 token。

    真实 token 数要调 API 才知道（各家分词器不同），这里只要够用来做截断判断。
    """
    ascii_count = sum(1 for ch in text if ord(ch) < 128)
    return ascii_count // 4 + (len(text) - ascii_count)


def total_tokens(messages: Messages) -> int:
    return sum(estimate_tokens(m["content"]) for m in messages)


def _ensure_starts_with_user(messages: Messages) -> Messages:
    """Anthropic 要求 messages 的第一条必须是 user。"""
    while messages and messages[0]["role"] != "user":
        messages = messages[1:]
    return messages


def truncate(messages: Messages, budget: int) -> Messages:
    """从最新的往回保留，直到装不下为止。"""
    kept: Messages = []
    used = 0
    for m in reversed(messages):
        t = estimate_tokens(m["content"])
        if kept and used + t > budget:
            break
        kept.append(m)
        used += t
    kept.reverse()
    return _ensure_starts_with_user(kept)


async def summarize(
    messages: Messages,
    client: LLMClient,
    budget: int,
    *,
    keep_recent: int = 4,
) -> Messages:
    """把最近 keep_recent 条之前的历史压成一段摘要，拼在最前面。"""
    if total_tokens(messages) <= budget:
        return messages

    old, recent = messages[:-keep_recent], messages[-keep_recent:]
    if not old:
        return truncate(messages, budget)

    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in old)
    resp = await client.chat(
        [{"role": "user", "content": transcript}],
        system=(
            "把以下对话压缩成一段摘要，保留所有后续对话可能需要的事实"
            "（人名、数字、结论、未完成的任务）。不超过 200 字，只输出摘要本身。"
        ),
        max_tokens=1024,
    )
    logger.info(
        "压缩历史：%d 条 → 摘要 %d token（压缩前 %d token）",
        len(old),
        estimate_tokens(resp.result),
        total_tokens(old),
    )
    summary = {"role": "user", "content": f"[此前对话的摘要]\n{resp.result}"}
    return _ensure_starts_with_user([summary, *recent])


async def apply_strategy(
    messages: Messages, client: LLMClient, strategy: str, budget: int
) -> Messages:
    if total_tokens(messages) <= budget:
        return messages
    if strategy == "summarize":
        return await summarize(messages, client, budget)
    return truncate(messages, budget)
