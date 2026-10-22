import logging
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.llm.client import get_client
from app.llm.context import apply_strategy, total_tokens
from app.llm.structured import chat_structured
from app.repositories import conversations as repo

logger = logging.getLogger(__name__)

router = APIRouter()

SYSTEM_PROMPT = "你是一个简洁的助手，回答控制在三句话以内。"
PROMPT_VERSION = "v1"


class ChatRequest(BaseModel):
    message: str
    conversation_id: UUID | None = None


class ChatReply(BaseModel):
    conversation_id: UUID
    reply: str
    input_tokens: int
    output_tokens: int
    history_tokens: int = Field(description="送给模型的历史 token 估算（经过上下文策略之后）")


class TitleSchema(BaseModel):
    """让模型按这个结构返回对话标题。"""

    title: str = Field(description="不超过 12 个字的对话标题")


@router.post("/chat", response_model=ChatReply)
async def chat(req: ChatRequest) -> ChatReply:
    settings = get_settings()
    client = get_client()

    is_new = req.conversation_id is None
    conv_id = req.conversation_id or await repo.create_conversation(prompt_version=PROMPT_VERSION)

    history = await repo.list_messages(conv_id)
    history = await apply_strategy(
        history, client, settings.context_strategy, settings.context_token_budget
    )
    messages = [*history, {"role": "user", "content": req.message}]

    resp = await client.chat(messages, system=SYSTEM_PROMPT)

    await repo.add_message(conv_id, "user", req.message)
    await repo.add_message(
        conv_id,
        "assistant",
        resp.result,
        usage={
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "model": resp.model,
            "stop_reason": resp.stop_reason,
        },
    )

    if resp.stop_reason == "max_tokens":
        logger.warning("回答被 max_tokens 截断，conversation=%s", conv_id)

    # 新对话顺便生成一个标题，用结构化输出保证拿到的是合法 JSON
    if is_new:
        title = await chat_structured(
            client,
            [{"role": "user", "content": req.message}],
            TitleSchema,
            system="根据用户的第一句话，起一个简短的对话标题。",
            fallback=TitleSchema(title=req.message[:12]),
        )
        await repo.set_title(conv_id, title.title)

    return ChatReply(
        conversation_id=conv_id,
        reply=resp.result,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
        history_tokens=total_tokens(messages),
    )
