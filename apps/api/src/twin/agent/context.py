from collections.abc import Sequence
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.messages.utils import count_tokens_approximately, trim_messages

from twin.agent.prompts import format_sources

# Older user messages longer than this (typically pasted job descriptions)
# are shortened so they are not re-sent in full on every later turn.
LONG_MESSAGE_CHARS = 1_500


def _shorten(message: BaseMessage) -> BaseMessage:
    content = message.content
    if (
        isinstance(message, HumanMessage)
        and isinstance(content, str)
        and len(content) > LONG_MESSAGE_CHARS
    ):
        return HumanMessage(content[:LONG_MESSAGE_CHARS] + " […]")
    return message


def history(messages: Sequence[BaseMessage], max_tokens: int) -> list[BaseMessage]:
    """Most recent conversation that fits a token budget, starting on a user
    turn. The latest message is always kept intact."""
    if not messages:
        return []
    *older, latest = messages
    trimmed = trim_messages(
        [_shorten(m) for m in older] + [latest],
        max_tokens=max_tokens,
        token_counter=count_tokens_approximately,
        strategy="last",
        start_on="human",
        include_system=False,
    )
    return list(trimmed) or [latest]


def sources_message(documents: list[dict[str, Any]]) -> HumanMessage:
    """Retrieved passages go in a user-role message wrapped in tags: they are
    data, and must not carry system-level authority."""
    return HumanMessage(
        f"<sources>\n{format_sources(documents)}\n</sources>\n"
        "Answer my latest question using only these sources."
    )
