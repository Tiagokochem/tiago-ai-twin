import structlog
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage

from twin.agent import context
from twin.agent.citations import CitationStreamFilter, extract_citations, strip_invalid_markers
from twin.agent.deps import AgentDeps, Node, emit
from twin.agent.prompts import LANGUAGE_NAMES
from twin.agent.schemas import Followups
from twin.agent.state import TwinState
from twin.persona import MessageName

log = structlog.get_logger()


def make_answer(deps: AgentDeps) -> Node:
    async def answer(state: TwinState) -> TwinState:
        emit("status", "answering")
        intent = state.get("intent") or "about_tiago"
        mode = intent if intent in ("smalltalk", "job_fit") else "answer"
        documents = state.get("documents", []) if mode != "smalltalk" else []
        lang = state["lang"]
        prompt = deps.prompts.render(
            "answer",
            persona=deps.persona,
            lang=lang,
            language=LANGUAGE_NAMES[lang],
            channel=state.get("channel", "web"),
            mode=mode,
            requirements=state.get("requirements", []),
        )
        messages: list[BaseMessage] = [
            SystemMessage(prompt.text),
            *context.history(state.get("messages", []), deps.answer_history_tokens),
        ]
        if mode != "smalltalk":
            messages.append(context.sources_message(documents))

        markers = CitationStreamFilter(len(documents))
        parts: list[str] = []
        async for token in deps.llm.stream("answer", messages, prompt=prompt.ref):
            parts.append(token)
            if visible := markers.feed(token):
                emit("token", visible)
        if rest := markers.flush():
            emit("token", rest)

        text = strip_invalid_markers("".join(parts), len(documents)).strip()
        return {
            "response": text,
            "citations": extract_citations(text, documents, query=state["question"]),
            "messages": [AIMessage(text)],
        }

    return answer


def make_followups(deps: AgentDeps) -> Node:
    async def followups(state: TwinState) -> TwinState:
        prompt = deps.prompts.render(
            "followups", persona=deps.persona, language=LANGUAGE_NAMES[state["lang"]]
        )
        try:
            result = await deps.llm.structured(
                "followups",
                [
                    SystemMessage(prompt.text),
                    *context.history(state.get("messages", []), deps.followups_history_tokens),
                ],
                Followups,
                prompt=prompt.ref,
            )
        except Exception as exc:  # suggestions are optional; never fail the turn
            log.warning("agent.followups_failed", error=repr(exc))
            return {"followups": []}
        return {"followups": result.questions}

    return followups


def make_handoff(deps: AgentDeps) -> Node:
    async def handoff(state: TwinState) -> TwinState:
        reason = state.get("handoff_reason") or "unknown"
        name: MessageName = "unknown" if reason == "unknown" else "handoff"
        text = deps.persona.message(name, state["lang"])
        emit("token", text)
        return {"response": text, "handoff_reason": reason, "messages": [AIMessage(text)]}

    return handoff
