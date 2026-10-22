"""结构化输出：让模型稳定返回 JSON，用 Pydantic 校验，失败了带着错误信息重试。"""

import json
import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def extract_json(text: str) -> str:
    """模型爱把 JSON 包在 ```json 里，或者前后加一句解释。把花括号之间的部分抠出来。"""
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1].removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end > start else text


async def chat_structured(
    client: LLMClient,
    messages: list[dict[str, str]],
    schema: type[T],
    *,
    system: str = "",
    max_retries: int = 2,
    fallback: T | None = None,
) -> T:
    """要求模型按 schema 返回 JSON。

    解析/校验失败时，把错误信息作为新一轮消息发回去让它改正；
    次数用尽后，有 fallback 就返回 fallback，否则抛异常。
    """
    instruction = (
        f"{system}\n\n"
        "只输出一个 JSON 对象，不要代码块标记，不要任何解释文字。\n"
        f"必须符合这个 JSON Schema：\n"
        f"{json.dumps(schema.model_json_schema(), ensure_ascii=False)}"
    ).strip()

    convo = list(messages)
    for attempt in range(max_retries + 1):
        resp = await client.chat(convo, system=instruction, max_tokens=2048)
        raw = extract_json(resp.result)
        try:
            return schema.model_validate_json(raw)
        except (ValidationError, ValueError) as e:
            logger.warning("结构化输出第 %d 次解析失败：%s", attempt + 1, e)
            if attempt == max_retries:
                if fallback is not None:
                    logger.warning("重试用尽，使用兜底值")
                    return fallback
                raise
            # 把模型自己的错误输出和报错一起发回去，让它看着改
            convo = [
                *convo,
                {"role": "assistant", "content": resp.result},
                {
                    "role": "user",
                    "content": f"上面的输出无法通过校验：{e}\n请只输出符合 schema 的 JSON。",
                },
            ]
    raise RuntimeError("unreachable")
