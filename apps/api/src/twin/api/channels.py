import secrets
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Body, Header, HTTPException, Query, status

from twin.api.deps import ContainerDep
from twin.channels.evolution import parse_webhook

log = structlog.get_logger()

router = APIRouter(prefix="/v1/channels", tags=["channels"])


@router.post("/whatsapp")
async def whatsapp_webhook(
    container: ContainerDep,
    payload: Annotated[dict[str, Any], Body()],
    token: Annotated[str | None, Query()] = None,
    x_webhook_token: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    """Evolution API webhook (event MESSAGES_UPSERT). Configure it as
    https://<host>/api/v1/channels/whatsapp?token=<EVOLUTION_WEBHOOK_TOKEN>."""
    channel = container.whatsapp
    settings = container.settings
    if channel is None or settings.evolution_webhook_token is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "whatsapp channel disabled")
    expected = settings.evolution_webhook_token.get_secret_value()
    provided = token or x_webhook_token or ""
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")
    instance = payload.get("instance")
    if instance and instance != settings.evolution_instance:
        return {"status": "ignored"}

    message = parse_webhook(payload)
    if message is None:
        return {"status": "ignored"}
    accepted = channel.accept(message)
    log.info(
        "whatsapp.inbound", accepted=accepted, audio=message.is_audio, number=message.number[-4:]
    )
    return {"status": "queued" if accepted else "duplicate"}
