import logging
import re
from collections.abc import MutableMapping
from typing import Any

import structlog

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_CANDIDATE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
# Identifiers and timestamps that look numeric but are not personal data.
_SKIP_KEYS = {"timestamp", "request_id", "session", "session_id", "path", "thread_id"}


def _mask_phone(match: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", match.group())
    if len(digits) < 10:
        return match.group()
    return f"<phone …{digits[-4:]}>"


def redact(text: str) -> str:
    """Mask e-mails and phone numbers that end up in log messages."""
    return _PHONE_CANDIDATE.sub(_mask_phone, _EMAIL.sub("<email>", text))


def _redact_pii(_: Any, __: str, event: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    for key, value in event.items():
        if isinstance(value, str) and key not in _SKIP_KEYS:
            event[key] = redact(value)
    return event


def configure_logging(level: str = "INFO", json: bool = False) -> None:
    logging.basicConfig(format="%(message)s", level=level)
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _redact_pii,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
    )
