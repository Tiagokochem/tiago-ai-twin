from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from twin import __version__
from twin.db.models import Chunk, Document
from twin.db.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    response: Response, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict[str, object]:
    # The embeddable widget probes this from third-party sites to decide
    # whether to fall back to a plain WhatsApp button.
    response.headers["Access-Control-Allow-Origin"] = "*"
    try:
        await session.execute(text("SELECT 1"))
        documents = await session.scalar(select(func.count()).select_from(Document))
        chunks = await session.scalar(select(func.count()).select_from(Chunk))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "version": __version__, "database": "unreachable"}
    return {
        "status": "ok",
        "version": __version__,
        "database": "ok",
        "knowledge": {"documents": documents, "chunks": chunks},
    }
