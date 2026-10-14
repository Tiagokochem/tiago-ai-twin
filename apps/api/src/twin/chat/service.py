import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from twin.agent.state import Channel, Lang, turn_input
from twin.channels.notify import HandoffEvent, Notifier, SessionEndedEvent
from twin.db.models import ChatMessage, ChatSession, LLMCallRecord
from twin.llm.usage import UsageTracker, track_usage
from twin.persona import Persona

log = structlog.get_logger()


class SessionNotFoundError(LookupError):
    pass


class SessionBusyError(RuntimeError):
    """A turn is already running for this session."""


class SessionEndedError(RuntimeError):
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
        prompt_version: str | None = None,
    ) -> None:
        self.graph = graph
        self._sessionmaker = sessionmaker
        self.persona = persona
        self.notifier = notifier
        self._limits = limits or ChatLimits()
        self._callbacks = callbacks or []
        self._prompt_version = prompt_version
        self._background: set[asyncio.Task[None]] = set()
        self._busy: set[uuid.UUID] = set()

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
        async with self._sessionmaker() as db:
            ended = await db.scalar(
                update(ChatSession)
                .where(ChatSession.id == session_id, ChatSession.ended_at.is_(None))
                .values(ended_at=func.now())
                .returning(ChatSession.id)
            )
            await db.commit()
        session = await self.get_session(session_id)
        if ended is None or not session.messages:
            return
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

    async def end_idle_sessions(self, max_idle: timedelta) -> int:
        """End conversations with no activity for `max_idle` so the owner gets a summary."""
        cutoff = datetime.now(UTC) - max_idle
        async with self._sessionmaker() as db:
            ids = (
                await db.scalars(
                    select(ChatSession.id).where(
                        ChatSession.ended_at.is_(None),
                        ChatSession.message_count > 0,
                        ChatSession.last_activity_at < cutoff,
                    )
                )
            ).all()
        for session_id in ids:
            await self.end_session(session_id)
        return len(ids)

    async def request_human(self, session_id: uuid.UUID, note: str) -> None:
        """Explicit request to talk to the real person (e.g. /humano on WhatsApp)."""
        session = await self.get_session(session_id)
        async with self._sessionmaker() as db:
            stored = await db.get(ChatSession, session_id)
            assert stored is not None
            if stored.handoff_at is None:
                stored.handoff_at = func.now()
            await db.commit()
        await self._notify_handoff(
            session_id, note, Reply(lang=session.lang, handoff_reason="explicit_request")
        )

    async def start_turn(
        self, session_id: uuid.UUID, text: str, lang: Lang | None = None
    ) -> AsyncIterator[ChatEvent]:
        """Validate and record the user message, then run the turn in a
        detached task. The returned iterator streams its events; if the client
        goes away the turn still completes and is persisted.

        Raises SessionNotFoundError, SessionEndedError or SessionBusyError."""
        if session_id in self._busy:
            raise SessionBusyError(str(session_id))
        self._busy.add(session_id)
        try:
            async with self._sessionmaker() as db:
                session = await db.get(ChatSession, session_id)
                if session is None:
                    raise SessionNotFoundError(str(session_id))
                if session.ended_at is not None:
                    raise SessionEndedError(str(session_id))
                turn_lang: Lang = lang or session.lang  # type: ignore[assignment]
                channel: Channel = session.channel  # type: ignore[assignment]
                if (
                    session.message_count >= self._limits.max_messages
                    or session.total_tokens >= self._limits.max_tokens
                ):
                    self._busy.discard(session_id)
                    return self._limit_reached(turn_lang)
                db.add(ChatMessage(session_id=session_id, role="user", content=text))
                session.message_count += 1
                session.last_activity_at = func.now()
                await db.commit()
        except BaseException:
            self._busy.discard(session_id)
            raise

        queue: asyncio.Queue[ChatEvent | None] = asyncio.Queue()
        task = asyncio.create_task(self._run_turn(session_id, text, turn_lang, channel, queue))
        self._background.add(task)
        task.add_done_callback(self._background.discard)
        return self._drain_queue(queue)

    async def stream_reply(
        self, session_id: uuid.UUID, text: str, lang: Lang | None = None
    ) -> AsyncIterator[ChatEvent]:
        async for event in await self.start_turn(session_id, text, lang):
            yield event

    async def _limit_reached(self, lang: Lang) -> AsyncIterator[ChatEvent]:
        message = self.persona.message("limit_reached", lang)
        yield ChatEvent("token", message)
        yield ChatEvent("done", {"limit_reached": True})

    @staticmethod
    async def _drain_queue(queue: asyncio.Queue[ChatEvent | None]) -> AsyncIterator[ChatEvent]:
        while (event := await queue.get()) is not None:
            yield event

    async def _run_turn(
        self,
        session_id: uuid.UUID,
        text: str,
        lang: Lang,
        channel: Channel,
        queue: asyncio.Queue[ChatEvent | None],
    ) -> None:
        started = time.perf_counter()
        config: RunnableConfig = {
            "configurable": {"thread_id": str(session_id)},
            "run_name": "twin-turn",
            "metadata": {
                "session_id": str(session_id),
                "channel": channel,
                "prompt_version": self._prompt_version,
            },
            "callbacks": self._callbacks,
        }
        streamed = False
        try:
            with track_usage() as usage:
                values: dict[str, Any]
                try:
                    async for chunk in self.graph.astream(
                        turn_input(text, lang, channel), config, stream_mode="custom"
                    ):
                        streamed = streamed or chunk["event"] == "token"
                        queue.put_nowait(ChatEvent(chunk["event"], chunk["data"]))
                    values = (await self.graph.aget_state(config)).values
                except Exception as exc:
                    log.exception("chat.turn_failed", session=str(session_id), error=repr(exc))
                    message = self.persona.message("unavailable", lang)
                    await self._repair_state(config, message)
                    if not streamed:
                        queue.put_nowait(ChatEvent("token", message))
                    values = {"response": message, "lang": lang, "intent": "error"}

                reply = Reply(
                    text=values.get("response", ""),
                    intent=values.get("intent"),
                    lang=values.get("lang", lang),
                    citations=values.get("citations", []),
                    followups=values.get("followups", []),
                    handoff_reason=values.get("handoff_reason"),
                    documents=values.get("documents", []),
                    usage=usage.summary(),
                )
                queue.put_nowait(
                    ChatEvent(
                        "final",
                        {
                            "response": reply.text,
                            "intent": reply.intent,
                            "lang": reply.lang,
                            "citations": reply.citations,
                            "followups": reply.followups,
                            "handoff": reply.handoff_reason,
                            "contact_link": self.persona.owner_contact_link,
                        },
                    )
                )
                latency_ms = int((time.perf_counter() - started) * 1000)
                message_id = await self._persist(
                    session_id, reply, usage, latency_ms, bool(values.get("degraded"))
                )
            if reply.handoff_reason:
                await self._notify_handoff(session_id, text, reply)
            queue.put_nowait(
                ChatEvent(
                    "done",
                    {
                        "message_id": message_id,
                        "latency_ms": latency_ms,
                        "prompt_version": self._prompt_version,
                        **reply.usage,
                    },
                )
            )
        except Exception as exc:
            log.exception("chat.persist_failed", session=str(session_id), error=repr(exc))
            queue.put_nowait(ChatEvent("error", {"message": "internal error"}))
        finally:
            # Released before the stream ends so a caller can start the next turn.
            self._busy.discard(session_id)
            queue.put_nowait(None)

    async def _repair_state(self, config: RunnableConfig, message: str) -> None:
        """Close the failed turn in the checkpoint so the thread keeps
        alternating user/assistant messages."""
        try:
            await self.graph.aupdate_state(
                config, {"messages": [AIMessage(message)], "response": message}, as_node="refuse"
            )
        except Exception as exc:
            log.warning("chat.repair_failed", error=repr(exc))

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
            text=final.get("response") or "".join(parts).strip(),
            intent=final.get("intent"),
            lang=final.get("lang"),
            citations=final.get("citations", []),
            followups=final.get("followups", []),
            handoff_reason=final.get("handoff"),
            usage=done,
        )

    async def set_feedback(
        self, session_id: uuid.UUID, message_id: int, value: int, comment: str | None
    ) -> None:
        async with self._sessionmaker() as db:
            updated = await db.scalar(
                update(ChatMessage)
                .where(
                    ChatMessage.id == message_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.role == "assistant",
                )
                .values(feedback=value, feedback_comment=comment)
                .returning(ChatMessage.id)
            )
            await db.commit()
        if updated is None:
            raise SessionNotFoundError(f"{session_id}/{message_id}")

    async def record_usage(self, usage: UsageTracker, scope: str) -> None:
        """Persist LLM calls made outside a chat turn (e.g. job fit) so they
        count towards spend metrics and budgets."""
        async with self._sessionmaker() as db:
            db.add_all(_call_records(usage, scope))
            await db.commit()

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
                prompt_version=self._prompt_version,
                llm_calls=_call_records(usage, "chat"),
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
        """Wait for running turns and notifications (shutdown and tests)."""
        while self._background:
            await asyncio.gather(*self._background, return_exceptions=True)


def _call_records(usage: UsageTracker, scope: str) -> list[LLMCallRecord]:
    return [
        LLMCallRecord(
            scope=scope,
            node=c.node,
            prompt=c.prompt,
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
    ]
