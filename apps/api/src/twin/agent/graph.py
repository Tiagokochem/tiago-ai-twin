from dataclasses import dataclass
from typing import Any, Literal

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from pydantic import BaseModel, Field

from twin.agent import prompts
from twin.agent.citations import extract_citations, strip_invalid_markers
from twin.agent.guard import looks_like_injection
from twin.agent.state import HandoffReason, Intent, Lang, TwinState
from twin.llm.gateway import LLMGateway
from twin.persona import MessageName, Persona
from twin.rag.retriever import Retriever

log = structlog.get_logger()


class Analysis(BaseModel):
    intent: Intent
    lang: Lang
    search_query: str = Field(description="standalone keyword search query")
    handoff_reason: HandoffReason = "none"


class Grade(BaseModel):
    relevant_ids: list[int] = Field(description="ids of the useful passages")


class Rewrite(BaseModel):
    query: str


class Followups(BaseModel):
    questions: list[str] = Field(max_length=3)


@dataclass
class AgentDeps:
    llm: LLMGateway
    retriever: Retriever
    persona: Persona
    top_k: int = 6
    job_fit_top_k: int = 10
    max_rewrites: int = 1
    history_window: int = 10


def _emit(event: str, data: Any) -> None:
    get_stream_writer()({"event": event, "data": data})


def _history(state: TwinState, window: int) -> list[BaseMessage]:
    return list(state.get("messages", [])[-window:])


def build_graph(deps: AgentDeps, checkpointer: Checkpointer = None) -> CompiledStateGraph[Any]:
    persona = deps.persona

    async def guard(state: TwinState) -> TwinState:
        if looks_like_injection(state["question"]):
            log.info("agent.guard_blocked")
            return {"intent": "injection"}
        return {}

    async def analyze(state: TwinState) -> TwinState:
        _emit("status", "thinking")
        result = await deps.llm.structured(
            "analyze",
            [
                SystemMessage(prompts.router_prompt(persona)),
                *_history(state, deps.history_window),
            ],
            Analysis,
        )
        return {
            "intent": result.intent,
            "lang": result.lang,
            "search_query": result.search_query or state["question"],
            "handoff_reason": result.handoff_reason if result.intent == "handoff" else None,
        }

    async def retrieve(state: TwinState) -> TwinState:
        _emit("status", "searching")
        job_fit = state.get("intent") == "job_fit"
        query = state["question"] if job_fit else state["search_query"]
        result = await deps.retriever.search(
            query, state["lang"], top_k=deps.job_fit_top_k if job_fit else deps.top_k
        )
        return {
            "documents": [c.to_dict() for c in result.chunks],
            "degraded": state.get("degraded", False) or result.degraded,
        }

    async def grade(state: TwinState) -> TwinState:
        documents = state.get("documents", [])
        if not documents or state.get("intent") == "job_fit":
            return {}
        passages = "\n\n".join(
            f"<passage id={i}>\n{d['title']} > {d['heading']}\n{d['content']}\n</passage>"
            for i, d in enumerate(documents)
        )
        result = await deps.llm.structured(
            "grade",
            [
                SystemMessage(prompts.grader_prompt()),
                HumanMessage(f"Question: {state['search_query']}\n\n{passages}"),
            ],
            Grade,
        )
        keep = sorted({i for i in result.relevant_ids if 0 <= i < len(documents)})
        return {"documents": [documents[i] for i in keep]}

    async def rewrite(state: TwinState) -> TwinState:
        result = await deps.llm.structured(
            "rewrite",
            [
                SystemMessage(prompts.rewrite_prompt(state["lang"])),
                HumanMessage(
                    f"Question: {state['question']}\nPrevious query: {state['search_query']}"
                ),
            ],
            Rewrite,
        )
        return {"search_query": result.query, "retries": state.get("retries", 0) + 1}

    async def answer(state: TwinState) -> TwinState:
        _emit("status", "answering")
        documents = state.get("documents", []) if state.get("intent") != "smalltalk" else []
        system = prompts.answer_prompt(
            persona,
            state["lang"],
            documents,
            intent=state.get("intent") or "about_tiago",
            channel=state.get("channel", "web"),
        )
        parts: list[str] = []
        async for token in deps.llm.stream(
            "answer", [SystemMessage(system), *_history(state, deps.history_window)]
        ):
            parts.append(token)
            _emit("token", token)
        text = strip_invalid_markers("".join(parts).strip(), len(documents))
        return {
            "response": text,
            "citations": extract_citations(text, documents),
            "messages": [AIMessage(text)],
        }

    async def followups(state: TwinState) -> TwinState:
        try:
            result = await deps.llm.structured(
                "followups",
                [
                    SystemMessage(prompts.followups_prompt(persona, state["lang"])),
                    *_history(state, deps.history_window),
                ],
                Followups,
            )
        except Exception as exc:  # suggestions are optional; never fail the turn
            log.warning("agent.followups_failed", error=repr(exc))
            return {"followups": []}
        return {"followups": [q.strip() for q in result.questions if q.strip()][:3]}

    async def handoff(state: TwinState) -> TwinState:
        reason = state.get("handoff_reason") or "unknown"
        text = persona.message("unknown" if reason == "unknown" else "handoff", state["lang"])
        _emit("token", text)
        return {"response": text, "handoff_reason": reason, "messages": [AIMessage(text)]}

    async def refuse(state: TwinState) -> TwinState:
        name: MessageName = "refusal" if state.get("intent") == "injection" else "off_topic"
        text = persona.message(name, state.get("lang", persona.default_language))
        _emit("token", text)
        return {"response": text, "messages": [AIMessage(text)]}

    def after_guard(state: TwinState) -> Literal["refuse", "analyze"]:
        return "refuse" if state.get("intent") == "injection" else "analyze"

    def after_analyze(
        state: TwinState,
    ) -> Literal["retrieve", "answer", "handoff", "refuse"]:
        intent = state.get("intent")
        if intent in ("about_tiago", "job_fit"):
            return "retrieve"
        if intent == "smalltalk":
            return "answer"
        if intent == "handoff":
            return "handoff"
        return "refuse"

    def after_grade(state: TwinState) -> Literal["answer", "rewrite", "handoff"]:
        if state.get("documents"):
            return "answer"
        if state.get("retries", 0) < deps.max_rewrites:
            return "rewrite"
        return "handoff"

    def after_answer(state: TwinState) -> Literal["followups", "__end__"]:
        return "followups" if state.get("channel") in ("web", "widget") else "__end__"

    builder = StateGraph(TwinState)
    builder.add_node("guard", guard)
    builder.add_node("analyze", analyze)
    builder.add_node("retrieve", retrieve)
    builder.add_node("grade", grade)
    builder.add_node("rewrite", rewrite)
    builder.add_node("answer", answer)
    builder.add_node("followups", followups)
    builder.add_node("handoff", handoff)
    builder.add_node("refuse", refuse)

    builder.add_edge(START, "guard")
    builder.add_conditional_edges("guard", after_guard)
    builder.add_conditional_edges("analyze", after_analyze)
    builder.add_edge("retrieve", "grade")
    builder.add_conditional_edges("grade", after_grade)
    builder.add_edge("rewrite", "retrieve")
    builder.add_conditional_edges("answer", after_answer)
    builder.add_edge("followups", END)
    builder.add_edge("handoff", END)
    builder.add_edge("refuse", END)
    return builder.compile(checkpointer=checkpointer, name="tiago-twin")
