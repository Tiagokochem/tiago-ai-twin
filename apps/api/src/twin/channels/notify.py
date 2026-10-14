from dataclasses import dataclass, field
from typing import Protocol

import structlog

log = structlog.get_logger()


@dataclass(frozen=True)
class HandoffEvent:
    session_id: str
    channel: str
    lang: str
    reason: str
    question: str
    transcript: list[tuple[str, str]] = field(default_factory=list)
    # Recruiter's WhatsApp number when the conversation happened on WhatsApp.
    contact: str | None = None


@dataclass(frozen=True)
class SessionEndedEvent:
    session_id: str
    channel: str
    lang: str
    transcript: list[tuple[str, str]]
    contact: str | None = None


class Notifier(Protocol):
    async def handoff(self, event: HandoffEvent) -> None: ...

    async def session_ended(self, event: SessionEndedEvent) -> None: ...


class LogNotifier:
    """Default notifier: only logs. Replaced by WhatsApp when configured."""

    async def handoff(self, event: HandoffEvent) -> None:
        log.info("notify.handoff", session=event.session_id, reason=event.reason)

    async def session_ended(self, event: SessionEndedEvent) -> None:
        log.info("notify.session_ended", session=event.session_id, turns=len(event.transcript))
