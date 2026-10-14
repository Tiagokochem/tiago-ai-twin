import asyncio
import re
from collections import OrderedDict, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from twin.channels.evolution import InboundMessage, WhatsAppSender
from twin.channels.notify import HandoffEvent, SessionEndedEvent
from twin.chat.service import ChatService
from twin.db.models import ChatSession
from twin.persona import Lang, Persona
from twin.security.budget import BudgetGuard
from twin.security.rate_limit import RateLimiter
from twin.voice.speech import Speech, speakable

log = structlog.get_logger()

HUMAN_COMMANDS = {"/humano", "/human", "humano", "/tiago"}
RESET_COMMANDS = {"/novo", "/new", "/reset", "/reiniciar"}

_CITATION = re.compile(r"\s?\[(\d{1,2})\]")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_HEADING = re.compile(r"^#{1,6}\s*", re.MULTILINE)
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")


def format_for_whatsapp(text: str, citations: list[dict[str, Any]], lang: Lang) -> str:
    """Markdown answer with [n] markers -> WhatsApp text with a compact source list."""
    body = _CITATION.sub("", text)
    body = _BOLD.sub(r"*\1*", body)
    body = _HEADING.sub("", body)
    body = _LINK.sub(r"\1 (\2)", body).strip()
    if not citations:
        return body
    seen: list[str] = []
    for c in citations:
        label = c["title"] + (f" - {c['url']}" if c.get("url") else "")
        if label not in seen:
            seen.append(label)
    header = "Fontes" if lang == "pt" else "Sources"
    return f"{body}\n\n_{header}:_\n" + "\n".join(f"• {s}" for s in seen[:4])


def guess_lang(number: str) -> Lang:
    return "pt" if number.startswith("55") else "en"


class _Seen:
    """Small LRU of processed message ids (Evolution may deliver twice)."""

    def __init__(self, size: int = 5000) -> None:
        self._ids: OrderedDict[str, None] = OrderedDict()
        self._size = size

    def add(self, message_id: str) -> bool:
        if message_id in self._ids:
            return False
        self._ids[message_id] = None
        if len(self._ids) > self._size:
            self._ids.popitem(last=False)
        return True


class WhatsAppChannel:
    """Recruiter <-> bot conversations over WhatsApp.

    Messages are deduplicated, debounced per number (people often send
    several short messages in a row), processed one batch at a time per
    number, rate limited, and answered with text (plus a voice note when
    the recruiter sent audio).
    """

    def __init__(
        self,
        chat: ChatService,
        persona: Persona,
        sender: WhatsAppSender,
        speech: Speech | None,
        *,
        debounce_seconds: float = 2.5,
        idle_hours: float = 12,
        limiter: RateLimiter | None = None,
        budget: BudgetGuard | None = None,
    ) -> None:
        self.chat = chat
        self.persona = persona
        self.sender = sender
        self.speech = speech
        self.debounce_seconds = debounce_seconds
        self.idle = timedelta(hours=idle_hours)
        self.limiter = limiter or RateLimiter(8, 150)
        self.budget = budget
        self._seen = _Seen()
        self._pending: dict[str, list[InboundMessage]] = defaultdict(list)
        self._timers: dict[str, asyncio.Task[None]] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._warned: set[str] = set()

    def accept(self, message: InboundMessage) -> bool:
        """Queue an inbound message. Returns False for duplicates and the owner."""
        if message.number == self.persona.owner_whatsapp:
            return False
        if not self._seen.add(message.id):
            return False
        self._pending[message.number].append(message)
        if message.number not in self._timers:
            task = asyncio.create_task(self._flush_later(message.number))
            self._timers[message.number] = task
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        return True

    async def drain(self) -> None:
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def _flush_later(self, number: str) -> None:
        try:
            await asyncio.sleep(self.debounce_seconds)
            async with self._locks[number]:
                self._timers.pop(number, None)
                batch = self._pending.pop(number, [])
                if batch:
                    await self._process(number, batch)
        except Exception as exc:
            log.exception("whatsapp.process_failed", number=number[-4:], error=repr(exc))

    async def _process(self, number: str, batch: list[InboundMessage]) -> None:
        lang = guess_lang(number)
        # Limits are checked before any paid work (transcription, LLM).
        audio_count = sum(1 for m in batch if m.is_audio)
        if self.limiter.hit(number, cost=1 + audio_count) is not None:
            if number not in self._warned:
                self._warned.add(number)
                await self.sender.send_text(number, self.persona.message("slow_down", lang))
            return
        self._warned.discard(number)
        if self.budget is not None and await self.budget.exceeded():
            await self.sender.send_text(number, self.persona.message("unavailable", lang))
            return

        parts: list[str] = []
        had_audio = audio_count > 0
        for message in batch:
            if message.is_audio:
                text = await self._transcribe(message, lang)
                if text:
                    parts.append(text)
            elif message.text:
                parts.append(message.text)
        if not parts:
            await self.sender.send_text(number, self.persona.message("audio_failed", lang))
            return
        text = "\n".join(parts).strip()

        command = text.lower().strip()
        session = await self._session_for(number, lang, greet=command not in RESET_COMMANDS)
        session_lang: Lang = "pt" if session.lang == "pt" else "en"

        if command in RESET_COMMANDS:
            await self.chat.end_session(session.id)
            await self.chat.create_session("whatsapp", session_lang, external_id=number)
            await self.sender.send_text(number, self.persona.message("session_reset", session_lang))
            return
        if command in HUMAN_COMMANDS:
            await self.chat.request_human(session.id, text)
            await self.sender.send_text(
                number, self.persona.message("human_requested", session_lang)
            )
            return

        await self.sender.typing(number)
        reply = await self.chat.reply(session.id, text)
        reply_lang: Lang = "pt" if (reply.lang or session_lang) == "pt" else "en"
        await self.sender.send_text(
            number, format_for_whatsapp(reply.text, reply.citations, reply_lang)
        )
        if had_audio and self.speech and reply.text:
            try:
                audio = b"".join(
                    [c async for c in self.speech.synthesize(speakable(reply.text), reply_lang)]
                )
                await self.sender.send_audio(number, audio)
            except Exception as exc:
                log.error("whatsapp.tts_failed", error=repr(exc))

    async def _transcribe(self, message: InboundMessage, lang: Lang) -> str:
        if self.speech is None:
            return ""
        try:
            audio = await self.sender.media_bytes(message)
            return (await self.speech.transcribe(audio, "voice.ogg", lang)).strip()
        except Exception as exc:
            log.error("whatsapp.transcribe_failed", error=repr(exc))
            return ""

    async def _session_for(self, number: str, lang: Lang, *, greet: bool) -> ChatSession:
        session = await self.chat.find_active_session("whatsapp", number)
        if session is not None:
            last = session.last_activity_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            if datetime.now(UTC) - last <= self.idle:
                return session
            await self.chat.end_session(session.id)
        session = await self.chat.create_session("whatsapp", lang, external_id=number)
        if greet:
            await self.sender.send_text(number, self.persona.message("whatsapp_welcome", lang))
        return session


REASONS = {
    "salary": "pretensão salarial",
    "offer": "proposta / contrato",
    "scheduling": "agendamento",
    "personal": "dados pessoais",
    "explicit_request": "pediu para falar com você",
    "unknown": "pergunta sem resposta nas fontes",
}


def _excerpt(transcript: list[tuple[str, str]], limit: int = 6) -> str:
    lines = []
    for role, content in transcript[-limit:]:
        who = "Recrutador" if role == "user" else "Tiago AI"
        text = " ".join(content.split())
        lines.append(f"*{who}:* {text[:280]}{'…' if len(text) > 280 else ''}")
    return "\n".join(lines)


class WhatsAppNotifier:
    """Sends handoffs and interview summaries to the owner's main WhatsApp,
    from the bot number. The owner never talks to the bot directly."""

    def __init__(self, sender: WhatsAppSender, owner_number: str, public_url: str | None) -> None:
        self.sender = sender
        self.owner = owner_number
        self.public_url = public_url.rstrip("/") if public_url else None

    def _links(self, session_id: str, contact: str | None) -> str:
        lines = []
        if contact:
            lines.append(f"Contato do recrutador: https://wa.me/{contact}")
        if self.public_url:
            lines.append(f"Transcrição: {self.public_url}/api/v1/sessions/{session_id}/transcript")
        return "\n".join(lines)

    async def handoff(self, event: HandoffEvent) -> None:
        reason = REASONS.get(event.reason, event.reason)
        text = (
            f"*Tiago AI - handoff* ({event.channel})\n"
            f"Motivo: {reason}\n"
            f"Pergunta: {event.question[:500]}\n\n"
            f"{_excerpt(event.transcript)}\n\n{self._links(event.session_id, event.contact)}"
        )
        await self.sender.send_text(self.owner, text.strip())

    async def session_ended(self, event: SessionEndedEvent) -> None:
        questions = [c for r, c in event.transcript if r == "user"]
        if not questions:
            return
        listed = "\n".join(
            f"{i}. {' '.join(q.split())[:160]}" for i, q in enumerate(questions[:10], 1)
        )
        text = (
            f"*Tiago AI - resumo da entrevista* ({event.channel}, {event.lang})\n"
            f"{len(questions)} pergunta(s):\n{listed}\n\n"
            f"{self._links(event.session_id, event.contact)}"
        )
        await self.sender.send_text(self.owner, text.strip())
