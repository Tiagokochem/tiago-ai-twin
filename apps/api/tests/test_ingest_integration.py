import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import func, literal_column, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from twin.db.models import Base, Chunk, Document
from twin.rag.embeddings import HashEmbedder
from twin.rag.ingest import ingest
from twin.rag.loader import load_knowledge

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL not set"),
]


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    assert DATABASE_URL
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s
    await engine.dispose()


async def test_ingest_is_incremental(session: AsyncSession, knowledge_dir: Path) -> None:
    embedder = HashEmbedder()

    first = await ingest(session, load_knowledge(knowledge_dir), embedder)
    assert sorted(first.added) == ["en/profile", "pt/profile"]

    second = await ingest(session, load_knowledge(knowledge_dir), embedder)
    assert second.added == second.updated == []
    assert second.chunks_embedded == 0

    (knowledge_dir / "en" / "profile.md").unlink()
    (knowledge_dir / "pt" / "perfil.md").write_text(
        "---\nid: profile\ntitle: Perfil\nlang: pt\nkind: profile\n---\n## Resumo\nNovo texto.\n",
        encoding="utf-8",
    )
    third = await ingest(session, load_knowledge(knowledge_dir), embedder)
    assert third.updated == ["pt/profile"]
    assert third.removed == ["en/profile"]
    assert await session.scalar(select(func.count()).select_from(Document)) == 1


async def test_full_text_uses_document_language(session: AsyncSession, knowledge_dir: Path) -> None:
    await ingest(session, load_knowledge(knowledge_dir), HashEmbedder())

    # Portuguese stemming: "desenvolvedores" matches "Desenvolvedor".
    query = func.websearch_to_tsquery(literal_column("'portuguese'::regconfig"), "desenvolvedores")
    hits = await session.scalars(select(Chunk.document_key).where(Chunk.tsv.op("@@")(query)))
    assert list(hits) == ["pt/profile"]
