from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import Any, Protocol

from langgraph.config import get_stream_writer

from twin.agent.job_fit import JobFitService
from twin.agent.prompts import PromptRegistry, default_registry
from twin.agent.state import TwinState
from twin.llm.gateway import LLMGateway
from twin.persona import Persona
from twin.rag.retriever import Retriever


class Node(Protocol):
    def __call__(self, state: TwinState) -> Awaitable[TwinState]: ...


@dataclass
class AgentDeps:
    llm: LLMGateway
    retriever: Retriever
    persona: Persona
    prompts: PromptRegistry = field(default_factory=default_registry)
    job_fit: JobFitService | None = None
    top_k: int = 6
    job_fit_top_k: int = 10
    max_rewrites: int = 1
    # Token budgets for the conversation history sent to each kind of call.
    router_history_tokens: int = 1_500
    answer_history_tokens: int = 3_000
    followups_history_tokens: int = 1_000

    def __post_init__(self) -> None:
        if self.job_fit is None:
            self.job_fit = JobFitService(
                self.llm,
                self.retriever,
                self.persona,
                self.prompts,
                max_sources=self.job_fit_top_k,
            )


def emit(event: str, data: Any) -> None:
    get_stream_writer()({"event": event, "data": data})
