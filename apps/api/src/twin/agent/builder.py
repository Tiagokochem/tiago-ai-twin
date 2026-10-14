from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer

from twin.agent import nodes, routing
from twin.agent.deps import AgentDeps
from twin.agent.state import TwinState


def build_graph(deps: AgentDeps, checkpointer: Checkpointer = None) -> CompiledStateGraph[Any]:
    """guard → analyze → (retrieve → grade ⟲ rewrite) → answer, with
    follow-ups in parallel; handoff and refuse are terminal."""
    builder = StateGraph(TwinState)
    builder.add_node("guard", nodes.make_guard(deps))
    builder.add_node("analyze", nodes.make_analyze(deps))
    builder.add_node("retrieve", nodes.make_retrieve(deps))
    builder.add_node("grade", nodes.make_grade(deps))
    builder.add_node("rewrite", nodes.make_rewrite(deps))
    builder.add_node("answer", nodes.make_answer(deps))
    builder.add_node("followups", nodes.make_followups(deps))
    builder.add_node("handoff", nodes.make_handoff(deps))
    builder.add_node("refuse", nodes.make_refuse(deps))

    builder.add_edge(START, "guard")
    builder.add_conditional_edges("guard", routing.after_guard)
    builder.add_conditional_edges(
        "analyze",
        routing.after_analyze,
        ["retrieve", "answer", "followups", "handoff", "refuse"],
    )
    builder.add_edge("retrieve", "grade")
    builder.add_conditional_edges("grade", routing.make_after_grade(deps.max_rewrites))
    builder.add_edge("rewrite", "retrieve")
    for terminal in ("answer", "followups", "handoff", "refuse"):
        builder.add_edge(terminal, END)
    return builder.compile(checkpointer=checkpointer, name="tiago-twin")
