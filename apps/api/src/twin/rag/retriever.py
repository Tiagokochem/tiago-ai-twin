from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Protocol

import structlog
from sqlalchemy import Text, cast, func, select
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from twin.db.models import Chunk, Document
from twin.rag.embeddings import Embedder
from twin.rag.ingest import TEXT_SEARCH_CONFIG

log = structlog.get_logger()


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_key: str
    title: str
    kind: str
    url: str | None
    heading: str
    content: str
    score: float
    vector_rank: int | None = None
    text_rank: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    degraded: bool = False


class Retriever(Protocol):
    async def search(
        self, query: str, lang: str, top_k: int = 6, kinds: Sequence[str] | None = None
    ) -> RetrievalResult: ...


def reciprocal_rank_fusion(rankings: Sequence[Sequence[int]], k: int = 60) -> dict[int, float]:
    """Combine ranked id lists: score(d) = sum(1 / (k + rank)), rank starting at 1."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return scores


class HybridRetriever:
    """pgvector cosine search + Postgres full-text search, fused with RRF.

    Full-text uses OR semantics (any stemmed term matches) so natural
    questions still hit; vector search covers paraphrases. If embeddings are
    unavailable the retriever degrades to full-text only.
    """

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        embedder: Embedder | None,
        candidates: int = 20,
        rrf_k: int = 60,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._embedder = embedder
        self._candidates = candidates
        self._rrf_k = rrf_k

    async def search(
        self, query: str, lang: str, top_k: int = 6, kinds: Sequence[str] | None = None
    ) -> RetrievalResult:
        degraded = False
        vector_ids: list[int] = []
        async with self._sessionmaker() as session:
            if self._embedder is not None:
                try:
                    [embedding] = await self._embedder.embed([query])
                    vector_ids = await self._vector_search(session, embedding, lang, kinds)
                except Exception as exc:
                    log.warning("retrieval.vector_failed", error=repr(exc))
                    degraded = True
            else:
                degraded = True
            text_ids = await self._text_search(session, query, lang, kinds)

            scores = reciprocal_rank_fusion([vector_ids, text_ids], self._rrf_k)
            top = sorted(scores, key=lambda i: -scores[i])[:top_k]
            if not top:
                return RetrievalResult([], degraded)

            rows = (
                await session.execute(
                    select(Chunk, Document).join(Document).where(Chunk.id.in_(top))
                )
            ).all()

        by_id = {chunk.id: (chunk, doc) for chunk, doc in rows}
        chunks = [
            RetrievedChunk(
                chunk_id=cid,
                document_key=by_id[cid][1].key,
                title=by_id[cid][1].title,
                kind=by_id[cid][1].kind,
                url=by_id[cid][1].url,
                heading=by_id[cid][0].heading,
                content=by_id[cid][0].content,
                score=round(scores[cid], 6),
                vector_rank=vector_ids.index(cid) + 1 if cid in vector_ids else None,
                text_rank=text_ids.index(cid) + 1 if cid in text_ids else None,
            )
            for cid in top
            if cid in by_id
        ]
        return RetrievalResult(chunks, degraded)

    async def _vector_search(
        self,
        session: AsyncSession,
        embedding: list[float],
        lang: str,
        kinds: Sequence[str] | None,
    ) -> list[int]:
        stmt = (
            select(Chunk.id)
            .join(Document)
            .where(Document.lang == lang)
            .order_by(Chunk.embedding.cosine_distance(embedding))
            .limit(self._candidates)
        )
        if kinds:
            stmt = stmt.where(Document.kind.in_(kinds))
        return list((await session.scalars(stmt)).all())

    async def _text_search(
        self, session: AsyncSession, query: str, lang: str, kinds: Sequence[str] | None
    ) -> list[int]:
        config = cast(TEXT_SEARCH_CONFIG.get(lang, "simple"), REGCONFIG)
        and_query = cast(func.plainto_tsquery(config, query), Text)
        or_query = func.to_tsquery(config, func.replace(and_query, "&", "|"))
        stmt = (
            select(Chunk.id)
            .join(Document)
            .where(Document.lang == lang, Chunk.tsv.op("@@")(or_query))
            .order_by(func.ts_rank_cd(Chunk.tsv, or_query).desc())
            .limit(self._candidates)
        )
        if kinds:
            stmt = stmt.where(Document.kind.in_(kinds))
        return list((await session.scalars(stmt)).all())
