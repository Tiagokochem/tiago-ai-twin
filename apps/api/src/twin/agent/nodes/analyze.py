from langchain_core.messages import SystemMessage

from twin.agent import context
from twin.agent.deps import AgentDeps, Node, emit
from twin.agent.schemas import Analysis
from twin.agent.state import TwinState


def make_analyze(deps: AgentDeps) -> Node:
    async def analyze(state: TwinState) -> TwinState:
        emit("status", "thinking")
        prompt = deps.prompts.render(
            "router", persona=deps.persona, default_lang=state.get("lang", "pt")
        )
        result = await deps.llm.structured(
            "analyze",
            [
                SystemMessage(prompt.text),
                *context.history(state.get("messages", []), deps.router_history_tokens),
            ],
            Analysis,
            prompt=prompt.ref,
        )
        handoff_reason = None
        if result.intent == "handoff":
            # The model may pick the handoff intent without a reason.
            handoff_reason = (
                result.handoff_reason if result.handoff_reason != "none" else "explicit_request"
            )
        return {
            "intent": result.intent,
            "lang": result.lang,
            "search_query": result.search_query.strip() or state["question"],
            "handoff_reason": handoff_reason,
        }

    return analyze
