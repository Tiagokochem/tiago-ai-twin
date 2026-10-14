from collections.abc import Callable
from typing import Literal

from twin.agent.state import TwinState

INTERACTIVE_CHANNELS = ("web", "widget")


def after_guard(state: TwinState) -> Literal["refuse", "analyze"]:
    return "refuse" if state.get("intent") == "injection" else "analyze"


def after_analyze(state: TwinState) -> list[str]:
    """Follow-up suggestions only depend on the conversation so far, so on
    interactive channels they are generated in parallel with the answer."""
    intent = state.get("intent")
    if intent in ("about_tiago", "job_fit"):
        branch = ["retrieve"]
    elif intent == "smalltalk":
        branch = ["answer"]
    elif intent == "handoff":
        return ["handoff"]
    else:
        return ["refuse"]
    if state.get("channel") in INTERACTIVE_CHANNELS:
        branch.append("followups")
    return branch


GradeRoute = Literal["answer", "rewrite", "handoff"]


def make_after_grade(max_rewrites: int) -> Callable[[TwinState], GradeRoute]:
    def after_grade(state: TwinState) -> Literal["answer", "rewrite", "handoff"]:
        if state.get("documents"):
            return "answer"
        if state.get("retries", 0) < max_rewrites:
            return "rewrite"
        return "handoff"

    return after_grade
