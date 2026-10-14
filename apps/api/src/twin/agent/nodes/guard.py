import structlog
from langchain_core.messages import AIMessage

from twin.agent.deps import AgentDeps, Node, emit
from twin.agent.guard import looks_like_injection
from twin.agent.state import TwinState
from twin.persona import MessageName

log = structlog.get_logger()


def make_guard(deps: AgentDeps) -> Node:
    async def guard(state: TwinState) -> TwinState:
        if looks_like_injection(state["question"]):
            log.info("agent.guard_blocked")
            return {"intent": "injection"}
        return {}

    return guard


def make_refuse(deps: AgentDeps) -> Node:
    async def refuse(state: TwinState) -> TwinState:
        name: MessageName = "refusal" if state.get("intent") == "injection" else "off_topic"
        text = deps.persona.message(name, state.get("lang", deps.persona.default_language))
        emit("token", text)
        return {"response": text, "messages": [AIMessage(text)]}

    return refuse
