"""对比截断和摘要两种上下文策略的代价。"""

import asyncio
import logging

from app.core.config import get_settings
from app.llm.anthropic import AnthropicClient
from app.llm.context import summarize, total_tokens, truncate

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

# 关键信息藏在最早的一轮里
HISTORY = [
    {"role": "user", "content": "我的工号是 A7731，记一下。"},
    {"role": "assistant", "content": "好的，已记住工号 A7731。"},
]
# 后面灌一堆无关的对话，把早期内容挤出预算
for i in range(8):
    HISTORY += [
        {"role": "user", "content": f"顺便问一下，第 {i} 个问题：介绍一下向量检索的原理，越详细越好。"},
        {"role": "assistant", "content": f"向量检索的核心是把文本映射到高维空间，通过余弦相似度衡量语义距离。（第 {i} 段详细解释，省略若干字）" + "补充说明。" * 20},
    ]

QUESTION = {"role": "user", "content": "我的工号是多少？"}
BUDGET = 400


async def main() -> None:
    s = get_settings()
    client = AnthropicClient(api_key=s.anthropic_api_key, model=s.anthropic_model)

    print(f"原始历史：{len(HISTORY)} 条消息，约 {total_tokens(HISTORY)} token")
    print(f"预算：{BUDGET} token\n")

    # 策略 1：截断
    t = truncate(HISTORY, BUDGET)
    print(f"【截断】保留 {len(t)} 条，约 {total_tokens(t)} token")
    r = await client.chat([*t, QUESTION], max_tokens=800)
    print(f"  问「我的工号是多少？」→ {r.result}\n")

    # 策略 2：摘要
    sm = await summarize(HISTORY, client, BUDGET)
    print(f"【摘要】压成 {len(sm)} 条，约 {total_tokens(sm)} token")
    print(f"  摘要内容：{sm[0]['content'][:120]}...")
    r = await client.chat([*sm, QUESTION], max_tokens=800)
    print(f"  问「我的工号是多少？」→ {r.result}")

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
