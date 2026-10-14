import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Any, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sse_starlette import EventSourceResponse

from twin.agent.state import Lang
from twin.api.deps import ContainerDep, client_hash, rate_limited
from twin.chat.service import SessionNotFoundError
from twin.chat.transcript import render_markdown

log = structlog.get_logger()

router = APIRouter(prefix="/v1", tags=["chat"])


class PersonaOut(BaseModel):
    name: str
    short_name: str
    role: dict[str, str]
    website: str
    github: str | None
    languages: list[str]
    contact_link: str
    starter_questions: dict[str, list[str]]
    messages: dict[str, dict[str, str]]


class SessionIn(BaseModel):
    lang: Lang = "pt"
    channel: Literal["web", "widget"] = "web"


class SessionOut(BaseModel):
    session_id: uuid.UUID
    lang: Lang
    greeting: str
    starter_questions: list[str]
    contact_link: str


class MessageOut(BaseModel):
    role: str
    content: str
    citations: list[dict[str, Any]]
    followups: list[str]
    handoff_reason: str | None
    created_at: datetime


class SessionDetail(BaseModel):
    session_id: uuid.UUID
    lang: str
    channel: str
    created_at: datetime
    messages: list[MessageOut]


class ChatIn(BaseModel):
    session_id: uuid.UUID
    message: str = Field(min_length=1)
    lang: Lang | None = None


@router.get("/persona", response_model=PersonaOut)
async def persona(container: ContainerDep) -> PersonaOut:
    p = container.persona
    names = ("disclaimer", "direct_contact")
    return PersonaOut(
        name=p.name,
        short_name=p.short_name,
        role=p.role.model_dump(),
        website=p.website,
        github=p.github,
        languages=list(p.languages),
        contact_link=p.owner_contact_link,
        starter_questions=p.starter_questions.model_dump(),
        messages={n: {lang: p.message(n, lang) for lang in ("pt", "en")} for n in names},  # type: ignore[arg-type]
    )


@router.post(
    "/sessions",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limited)],
)
async def create_session(
    body: SessionIn,
    container: ContainerDep,
    fingerprint: Annotated[str, Depends(client_hash)],
) -> SessionOut:
    session = await container.chat.create_session(body.channel, body.lang, client_hash=fingerprint)
    p = container.persona
    return SessionOut(
        session_id=session.id,
        lang=body.lang,
        greeting=p.message("disclaimer", body.lang),
        starter_questions=p.starter_questions.get(body.lang),
        contact_link=p.owner_contact_link,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: uuid.UUID, container: ContainerDep) -> SessionDetail:
    try:
        session = await container.chat.get_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found") from exc
    return SessionDetail(
        session_id=session.id,
        lang=session.lang,
        channel=session.channel,
        created_at=session.created_at,
        messages=[
            MessageOut(
                role=m.role,
                content=m.content,
                citations=m.citations,
                followups=m.followups,
                handoff_reason=m.handoff_reason,
                created_at=m.created_at,
            )
            for m in session.messages
        ],
    )


@router.get("/sessions/{session_id}/transcript", response_class=PlainTextResponse)
async def transcript(session_id: uuid.UUID, container: ContainerDep) -> Response:
    try:
        session = await container.chat.get_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found") from exc
    return PlainTextResponse(
        render_markdown(session, container.persona),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="tiago-ai-{session_id}.md"'},
    )


@router.post("/sessions/{session_id}/end", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(session_id: uuid.UUID, container: ContainerDep) -> None:
    try:
        await container.chat.end_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found") from exc


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: uuid.UUID, container: ContainerDep) -> None:
    await container.chat.delete_session(session_id)


@router.post("/chat", dependencies=[Depends(rate_limited)])
async def chat(body: ChatIn, request: Request, container: ContainerDep) -> EventSourceResponse:
    limit = container.settings.max_job_description_chars
    if len(body.message) > limit:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"message longer than {limit} characters"
        )
    try:
        await container.chat.get_session(body.session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found") from exc

    async def events() -> AsyncIterator[dict[str, str]]:
        try:
            async for event in container.chat.stream_reply(
                body.session_id, body.message.strip(), body.lang
            ):
                yield {"event": event.event, "data": json.dumps(event.data, ensure_ascii=False)}
        except Exception as exc:
            log.exception("chat.stream_failed", error=repr(exc))
            yield {"event": "error", "data": json.dumps({"message": "internal error"})}

    return EventSourceResponse(events(), ping=15, headers={"X-Accel-Buffering": "no"})
