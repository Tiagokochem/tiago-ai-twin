import argparse
import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import structlog
from sqlalchemy import cast, delete, func, insert, literal_column, select
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from twin.config import get_settings
from twin.db.models import Chunk, Document
from twin.db.session import get_sessionmaker
from twin.logging import configure_logging
from twin.rag.chunking import CHUNKING_VERSION, chunk_document
from twin.rag.embeddings import Embedder, HashEmbedder, OpenAIEmbedder
from twin.rag.loader import SourceDocument, load_knowledge

log = structlog.get_logger()

TEXT_SEARCH_CONFIG = {"pt": "portuguese", "en": "english"}


@dataclass
class IngestStats:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    chunks_embedded: int = 0


def content_hash(doc: SourceDocument, embedder: Embedder) -> str:
    payload = json.dumps(
        {
            "meta": doc.meta.model_dump(),
            "body": doc.body,
            "chunking": CHUNKING_VERSION,
            "model": f"{embedder.model}:{embedder.dimensions}",
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


async def ingest(
    session: AsyncSession, docs: list[SourceDocument], embedder: Embedder
) -> IngestStats:
    """Sync the knowledge base with `docs`. Only new or changed documents are
    re-embedded; documents missing from `docs` are removed."""
    stats = IngestStats()
    existing = dict((await session.execute(select(Document.key, Document.content_hash))).all())

    for doc in docs:
        digest = content_hash(doc, embedder)
        if existing.get(doc.key) == digest:
            stats.unchanged.append(doc.key)
            continue

        chunks = chunk_document(doc)
        vectors = await embedder.embed([c.embedding_text(doc.meta.title) for c in chunks])

        values = {
            "key": doc.key,
            "source_path": doc.path,
            "title": doc.meta.title,
            "lang": doc.meta.lang,
            "kind": doc.meta.kind,
            "url": doc.meta.url,
            "tags": doc.meta.tags,
            "content_hash": digest,
        }
        upsert = pg_insert(Document).values(**values)
        await session.execute(
            upsert.on_conflict_do_update(
                index_elements=[Document.key],
                set_={**values, "updated_at": func.now()},
            )
        )
        await session.execute(delete(Chunk).where(Chunk.document_key == doc.key))
        ts_config = cast(TEXT_SEARCH_CONFIG[doc.meta.lang], REGCONFIG)
        for chunk, vector in zip(chunks, vectors, strict=True):
            heading_tsv = func.setweight(
                func.to_tsvector(ts_config, chunk.heading), literal_column("'A'")
            )
            content_tsv = func.setweight(
                func.to_tsvector(ts_config, chunk.content), literal_column("'B'")
            )
            await session.execute(
                insert(Chunk).values(
                    document_key=doc.key,
                    ord=chunk.ord,
                    heading=chunk.heading,
                    content=chunk.content,
                    embedding=vector,
                    tsv=heading_tsv.op("||")(content_tsv),
                )
            )
        stats.chunks_embedded += len(chunks)
        (stats.updated if doc.key in existing else stats.added).append(doc.key)
        log.info("ingest.document", key=doc.key, chunks=len(chunks))

    removed = set(existing) - {d.key for d in docs}
    if removed:
        await session.execute(delete(Document).where(Document.key.in_(removed)))
        stats.removed = sorted(removed)

    await session.commit()
    return stats


class EmbedderNotConfiguredError(RuntimeError):
    pass


def build_embedder(offline: bool = False) -> Embedder:
    settings = get_settings()
    if offline:
        return HashEmbedder(settings.embedding_dimensions)
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value():
        raise EmbedderNotConfiguredError("OPENAI_API_KEY is not set")
    return OpenAIEmbedder(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )


async def run(knowledge_dir: Path, offline: bool, dry_run: bool) -> IngestStats | None:
    docs = load_knowledge(knowledge_dir)
    if dry_run:
        for doc in docs:
            print(f"{doc.key:45} {len(chunk_document(doc)):3} chunks  {doc.path}")
        return None
    embedder = build_embedder(offline)
    async with get_sessionmaker()() as session:
        return await ingest(session, docs, embedder)


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Ingest knowledge/ into pgvector")
    parser.add_argument("--dir", type=Path, default=settings.knowledge_dir)
    parser.add_argument("--offline", action="store_true", help="use the hash embedder")
    parser.add_argument("--dry-run", action="store_true", help="only list documents/chunks")
    args = parser.parse_args()

    configure_logging(settings.log_level)
    try:
        stats = asyncio.run(run(args.dir, args.offline, args.dry_run))
    except EmbedderNotConfiguredError as exc:
        raise SystemExit(f"{exc} (use --offline to test with the hash embedder)") from exc
    if stats is not None:
        print(json.dumps(asdict(stats), indent=2))


if __name__ == "__main__":
    main()
