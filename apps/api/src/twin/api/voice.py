import uuid
from collections.abc import AsyncIterator
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from twin.agent.state import Lang
from twin.api.deps import ContainerDep, rate_limit, within_budget
from twin.chat.service import SessionNotFoundError
from twin.voice.speech import Speech, speakable

log = structlog.get_logger()

router = APIRouter(prefix="/v1/voice", tags=["voice"])


class TranscriptOut(BaseModel):
    text: str


class SpeakIn(BaseModel):
    session_id: uuid.UUID
    message_id: int


def _speech(container: ContainerDep) -> Speech:
    if container.speech is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "voice is not configured")
    return container.speech


SpeechDep = Annotated[Speech, Depends(_speech)]


@router.post(
    "/transcribe",
    response_model=TranscriptOut,
    dependencies=[Depends(rate_limit(cost=2)), Depends(within_budget)],
)
async def transcribe(
    container: ContainerDep,
    speech: SpeechDep,
    audio: Annotated[UploadFile, File()],
    lang: Annotated[Lang | None, Form()] = None,
) -> TranscriptOut:
    limit = container.settings.max_audio_bytes
    data = await audio.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "audio too large")
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "empty audio")
    try:
        text = await speech.transcribe(data, audio.filename or "speech.webm", lang)
    except Exception as exc:
        log.error("voice.transcribe_failed", error=repr(exc))
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "transcription failed") from exc
    return TranscriptOut(text=text)


@router.post(
    "/speak",
    response_class=StreamingResponse,
    dependencies=[Depends(rate_limit(cost=2)), Depends(within_budget)],
)
async def speak(body: SpeakIn, container: ContainerDep, speech: SpeechDep) -> StreamingResponse:
    """Speak a stored assistant answer. Only persisted answers can be voiced,
    so the endpoint cannot be used as a free text-to-speech proxy."""
    try:
        message = await container.chat.get_assistant_message(body.session_id, body.message_id)
        session = await container.chat.get_session(body.session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found") from exc
    text = speakable(message.content)[: container.settings.max_tts_chars]
    lang: Lang = "pt" if session.lang == "pt" else "en"
    stream = speech.synthesize(text, lang)
    try:
        first = await anext(stream)
    except StopAsyncIteration:
        first = b""
    except Exception as exc:
        log.error("voice.speak_failed", error=repr(exc))
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "speech synthesis failed") from exc

    async def body_iter() -> AsyncIterator[bytes]:
        yield first
        async for chunk in stream:
            yield chunk

    return StreamingResponse(body_iter(), media_type="audio/mpeg")
