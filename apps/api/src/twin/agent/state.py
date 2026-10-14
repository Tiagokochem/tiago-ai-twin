from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph.message import add_messages

Lang = Literal["pt", "en"]
Channel = Literal["web", "widget", "whatsapp", "eval"]
Intent = Literal["about_tiago", "job_fit", "smalltalk", "handoff", "off_topic", "injection"]
HandoffReason = Literal[
    "salary", "offer", "scheduling", "personal", "explicit_request", "unknown", "none"
]


class TwinState(TypedDict, total=False):
    # Persisted across turns by the checkpointer (conversation memory).
    messages: Annotated[list[AnyMessage], add_messages]
    channel: Channel
    # Per-turn fields, reset by the chat service on every new user message.
    lang: Lang
    question: str
    intent: Intent | None
    search_query: str
    retries: int
    documents: list[dict[str, Any]]
    degraded: bool
    response: str
    citations: list[dict[str, Any]]
    followups: list[str]
    handoff_reason: HandoffReason | None


def turn_input(question: str, lang: Lang, channel: Channel) -> TwinState:
    return {
        "messages": [HumanMessage(question)],
        "channel": channel,
        "lang": lang,
        "question": question,
        "intent": None,
        "search_query": question,
        "retries": 0,
        "documents": [],
        "degraded": False,
        "response": "",
        "citations": [],
        "followups": [],
        "handoff_reason": None,
    }
