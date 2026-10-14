import time
import uuid

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

log = structlog.get_logger()

QUIET_PATHS = {"/health"}


class RequestContextMiddleware:
    """Request id + access log. Replaces uvicorn's access log, which would
    print query strings (the WhatsApp webhook token travels in one)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        incoming = headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if 0 < len(incoming) <= 64 else uuid.uuid4().hex[:16]
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message.setdefault("headers", []).append(
                    (b"x-request-id", request_id.encode("latin-1"))
                )
            await send(message)

        with structlog.contextvars.bound_contextvars(request_id=request_id):
            try:
                await self.app(scope, receive, send_with_id)
            finally:
                path = scope.get("path", "")
                if path.removeprefix(scope.get("root_path", "")) not in QUIET_PATHS:
                    log.info(
                        "http.request",
                        method=scope.get("method"),
                        path=path,
                        status=status,
                        duration_ms=int((time.perf_counter() - started) * 1000),
                    )
