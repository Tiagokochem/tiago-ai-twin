from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from twin.api.deps import require_admin
from twin.config import Settings, get_settings
from twin.db.session import get_session
from twin.observability.metrics import collect_metrics
from twin.rag.ingest import EmbedderNotConfiguredError, build_embedder, ingest
from twin.rag.loader import KnowledgeError, load_knowledge

router = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/ingest")
async def run_ingest(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    try:
        embedder = build_embedder()
        docs = load_knowledge(settings.knowledge_dir)
    except EmbedderNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except KnowledgeError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    stats = await ingest(session, docs, embedder)
    return asdict(stats)


@router.get("/metrics")
async def metrics(
    session: Annotated[AsyncSession, Depends(get_session)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> dict[str, Any]:
    return await collect_metrics(session, days)
