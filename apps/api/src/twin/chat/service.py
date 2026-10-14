import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import structlog
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from twin.agent.state import Channel, Lang, turn_input
from twin.channels.notify import HandoffEvent, Notifier, SessionEndedEvent
from twin.db.models import ChatMessage, ChatSession, LLMCallRecord
from twin.llm.gateway import AllProvidersFailedError
from twin.llm.usage import UsageTracker, track_usage
from twin.persona import Persona

log = structlog.get_logger()


class SessionNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class ChatEvent:
    event: str
    data: Any


@dataclass
class Reply:
    text: str = ""
    intent: str | None = None
    lang: str | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)
    followups: list[str] = field(default_factory=list)
    handoff_reason: str | None = None
    documents: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChatLimits:
    max_messages: int = 40
    max_tokens: int = 150_000


class ChatService:
    """Runs one conversation turn through the agent graph, streams events,
    and persists the transcript plus per-call LLM metrics."""

    def __init__(
        self,
        graph: CompiledStateGraph[Any],
        sessionmaker: async_sessionmaker[AsyncSession],
        persona: Persona,
        notifier: Notifier,
        limits: ChatLimits | None = None,
        callbacks: list[BaseCallbackHandler] | None = None,
    ) -> None:
        self.graph = graph
        self._sessionmaker = sessionmaker
        self.persona = persona
        self.notifier = notifier
        self._limits = limits or ChatLimits()
        self._callbacks = callbacks or []
        self._background: set[asyncio.Task[None]] = set()

    async def create_session(
        self,
        channel: Channel,
        lang: Lang,
        *,
        external_id: str | None = None,
        client_hash: str | None = None,
    ) -> ChatSession:
        async with self._sessionmaker() as db:
            session = ChatSession(
                id=uuid.uuid4(),
                channel=channel,
                lang=lang,
                external_id=external_id,
                client_hash=client_hash,
            )
            db.add(session)
            await db.commit()
            return session

    async def get_session(self, session_id: uuid.UUID) -> ChatSession:
        async with self._sessionmaker() as db:
            session = await db.scalar(
                select(ChatSession)
                .where(ChatSession.id == session_id)
                .options(selectinload(ChatSession.messages))
            )
        if session is None:
            raise SessionNotFoundError(str(session_id))
        return session

    async def get_assistant_message(self, session_id: uuid.UUID, message_id: int) -> ChatMessage:
        async with self._sessionmaker() as db:
            message = await db.scalar(
                select(ChatMessage).where(
                    ChatMessage.id == message_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.role == "assistant",
                )
            )
        if message is None:
            raise SessionNotFoundError(f"{session_id}/{message_id}")
        return message

    async def find_active_session(self, channel: Channel, external_id: str) -> ChatSession | None:
        async with self._sessionmaker() as db:
            return await db.scalar(
                select(ChatSession)
                .where(
                    ChatSession.channel == channel,
                    ChatSession.external_id == external_id,
                    ChatSession.ended_at.is_(None),
                )
                .order_by(ChatSession.last_activity_at.desc())
                .limit(1)
            )

    async def delete_session(self, session_id: uuid.UUID) -> None:
        async with self._sessionmaker() as db:
            session = await db.get(ChatSession, session_id)
            if session is not None:
                await db.delete(session)
                await db.commit()
        checkpointer = self.graph.checkpointer
        if checkpointer is not None and hasattr(checkpointer, "adelete_thread"):
            await checkpointer.adelete_thread(str(session_id))

    async def end_session(self, session_id: uuid.UUID) -> None:
        session = await self.get_session(session_id)
        if session.ended_at is not None:
            return
        async with self._sessionmaker() as db:
            stored = await db.get(ChatSession, session_id)
            assert stored is not None
            stored.ended_at = func.now()
            await db.commit()
        if session.messages:
            self._spawn(
                self.notifier.session_ended(
                    SessionEndedEvent(
                        session_id=str(session.id),
                        channel=session.channel,
                        lang=session.lang,
                        transcript=[(m.role, m.content) for m in session.messages],
                        contact=session.external_id,
                    )
                )
            )

    async def stream_reply(
        self, session_id: uuid.UUID, text: str, lang: Lang | None = None
    ) -> AsyncIterator[ChatEvent]:
        started = time.perf_counter()
        async with self._sessionmaker() as db:
            session = await db.get(ChatSession, session_id)
            if session is None:
                raise SessionNotFoundError(str(session_id))
            turn_lang: Lang = lang or session.lang  # type: ignore[assignment]
            channel: Channel = session.channel  # type: ignore[assignment]
            if (
                session.message_count >= self._limits.max_messages
                or session.total_tokens >= self._limits.max_tokens
            ):
                yield ChatEvent("token", self.persona.message("limit_reached", turn_lang))
                yield ChatEvent("done", {"limit_reached": True})
                return
            db.add(ChatMessage(session_id=session_id, role="user", content=text))
            session.message_count += 1
            session.last_activity_at = func.now()
            await db.commit()

        config: RunnableConfig = {
            "configurable": {"thread_id": str(session_id)},
            "run_name": "twin-turn",
            "metadata": {"session_id": str(session_id), "channel": channel},
            "callbacks": self._callbacks,
        }
        values: dict[str, Any]
        with track_usage() as usage:
            try:
                async for chunk in self.graph.astream(
                    turn_input(text, turn_lang, channel), config, stream_mode="custom"
                ):
                    yield ChatEvent(chunk["event"], chunk["data"])
                values = (await self.graph.aget_state(config)).values
            except AllProvidersFailedError as exc:
                log.error("chat.providers_failed", session=str(session_id), error=str(exc))
                message = self.persona.message("unavailable", turn_lang)
                yield ChatEvent("token", message)
                values = {"response": message, "lang": turn_lang, "intent": "error"}

            reply = Reply(
                text=values.get("response", ""),
                intent=values.get("intent"),
                lang=values.get("lang", turn_lang),
                citations=values.get("citations", []),
                followups=values.get("followups", []),
                handoff_reason=values.get("handoff_reason"),
                documents=values.get("documents", []),
                usage=usage.summary(),
            )
            yield ChatEvent(
                "final",
                {
                    "intent": reply.intent,
                    "lang": reply.lang,
                    "citations": reply.citations,
                    "followups": reply.followups,
                    "handoff": reply.handoff_reason,
                    "contact_link": self.persona.owner_contact_link,
                },
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            message_id = await self._persist(
                session_id, reply, usage, latency_ms, bool(values.get("degraded"))
            )

        if reply.handoff_reason:
            await self._notify_handoff(session_id, text, reply)
        yield ChatEvent("done", {"message_id": message_id, "latency_ms": latency_ms, **reply.usage})

    async def reply(self, session_id: uuid.UUID, text: str, lang: Lang | None = None) -> Reply:
        """Non-streaming turn (WhatsApp, evals)."""
        parts: list[str] = []
        final: dict[str, Any] = {}
        done: dict[str, Any] = {}
        async for event in self.stream_reply(session_id, text, lang):
            if event.event == "token":
                parts.append(event.data)
            elif event.event == "final":
                final = event.data
            elif event.event == "done":
                done = event.data
        return Reply(
            text="".join(parts).strip(),
            intent=final.get("intent"),
            lang=final.get("lang"),
            citations=final.get("citations", []),
            followups=final.get("followups", []),
            handoff_reason=final.get("handoff"),
            usage=done,
        )

    async def _persist(
        self,
        session_id: uuid.UUID,
        reply: Reply,
        usage: UsageTracker,
        latency_ms: int,
        degraded: bool,
    ) -> int:
        async with self._sessionmaker() as db:
            message = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=reply.text,
                intent=reply.intent,
                citations=reply.citations,
                followups=reply.followups,
                handoff_reason=reply.handoff_reason,
                degraded=degraded,
                latency_ms=latency_ms,
                llm_calls=[
                    LLMCallRecord(
                        node=c.node,
                        provider=c.provider,
                        model=c.model,
                        latency_ms=c.latency_ms,
                        input_tokens=c.input_tokens,
                        output_tokens=c.output_tokens,
                        cost_usd=c.cost_usd,
                        ok=c.ok,
                        fallback=c.fallback,
                        error=c.error,
                    )
                    for c in usage.calls
                ],
            )
            db.add(message)
            session = await db.get(ChatSession, session_id)
            assert session is not None
            session.total_tokens += usage.total_tokens
            session.total_cost_usd += usage.total_cost_usd
            if reply.handoff_reason and session.handoff_at is None:
                session.handoff_at = func.now()
            await db.commit()
            return message.id

    async def _notify_handoff(self, session_id: uuid.UUID, question: str, reply: Reply) -> None:
        session = await self.get_session(session_id)
        event = HandoffEvent(
            session_id=str(session_id),
            channel=session.channel,
            lang=reply.lang or session.lang,
            reason=reply.handoff_reason or "unknown",
            question=question,
            transcript=[(m.role, m.content) for m in session.messages],
            contact=session.external_id,
        )
        self._spawn(self.notifier.handoff(event))

    def _spawn(self, coro: Any) -> None:
        task: asyncio.Task[None] = asyncio.create_task(self._safe(coro))
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    @staticmethod
    async def _safe(coro: Any) -> None:
        try:
            await coro
        except Exception as exc:
            log.error("notify.failed", error=repr(exc))

    async def drain(self) -> None:
        """Wait for background notifications (used on shutdown and in tests)."""
        if self._background:
            await asyncio.gather(*self._background, return_exceptions=True)
