from collections.abc import AsyncIterator, Callable, Sequence
from typing import Any

from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from twin.llm.providers import SchemaT, Tier
from twin.llm.usage import TokenUsage
from twin.rag.retriever import RetrievalResult, RetrievedChunk

Responder = BaseModel | Callable[[Sequence[BaseMessage]], BaseModel]


class ScriptedProvider:
    """Deterministic ChatProvider: structured replies keyed by schema name."""

    def __init__(
        self,
        name: str = "scripted",
        structured: dict[str, Responder] | None = None,
        answer: str | Callable[[Sequence[BaseMessage]], str] = "Answer.",
        fail: bool = False,
    ) -> None:
        self.name = name
        self._structured = structured or {}
        self._answer = answer
        self._fail = fail
        self.calls: list[tuple[str, Sequence[BaseMessage]]] = []

    def model_name(self, tier: Tier) -> str:
        return f"{self.name}-{tier}"

    async def structured(
        self, messages: Sequence[BaseMessage], schema: type[SchemaT], tier: Tier
    ) -> tuple[SchemaT, TokenUsage]:
        self.calls.append((schema.__name__, messages))
        if self._fail:
            raise ConnectionError(f"{self.name} is down")
        responder = self._structured[schema.__name__]
        result = responder(messages) if callable(responder) else responder
        assert isinstance(result, schema)
        return result, TokenUsage(100, 20)

    async def stream(
        self, messages: Sequence[BaseMessage], tier: Tier
    ) -> AsyncIterator[str | TokenUsage]:
        self.calls.append(("stream", messages))
        if self._fail:
            raise ConnectionError(f"{self.name} is down")
        text = self._answer(messages) if callable(self._answer) else self._answer
        for word in text.split(" "):
            yield word + " "
        yield TokenUsage(500, 50)


def chunk(
    n: int, title: str = "Project", heading: str = "Overview", **extra: Any
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=n,
        document_key=f"en/doc-{n}",
        title=title,
        kind="project",
        url=None,
        heading=heading,
        content=extra.get("content", f"Content {n}"),
        score=1.0 / n,
    )


class FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self.chunks = chunks or []
        self.queries: list[tuple[str, str]] = []

    async def search(
        self, query: str, lang: str, top_k: int = 6, kinds: Sequence[str] | None = None
    ) -> RetrievalResult:
        self.queries.append((query, lang))
        return RetrievalResult(self.chunks[:top_k])
