import base64
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
import structlog

log = structlog.get_logger()


@dataclass(frozen=True)
class InboundMessage:
    id: str
    number: str
    name: str | None
    text: str
    is_audio: bool
    raw: dict[str, Any]


def _sender(key: dict[str, Any]) -> str | None:
    """Phone digits of the sender. Newer WhatsApp 'LID' addressing hides the
    number in remoteJid and exposes it in senderPn / remoteJidAlt."""
    for candidate in (key.get("remoteJid"), key.get("senderPn"), key.get("remoteJidAlt")):
        if isinstance(candidate, str) and candidate.endswith("@s.whatsapp.net"):
            return candidate.split("@", 1)[0].split(":", 1)[0]
    return None


def parse_webhook(payload: dict[str, Any]) -> InboundMessage | None:
    """Extract a recruiter message from an Evolution API v2 `messages.upsert`
    event. Returns None for anything we should ignore (own messages, groups,
    status updates, reactions, stickers...)."""
    event = str(payload.get("event", "")).lower().replace("_", ".")
    if event != "messages.upsert":
        return None
    data = payload.get("data")
    if isinstance(data, list):
        data = data[0] if data else None
    if not isinstance(data, dict):
        return None
    key = data.get("key") or {}
    if key.get("fromMe"):
        return None
    number = _sender(key)
    message_id = key.get("id")
    if not number or not message_id:
        return None

    message = data.get("message") or {}
    text = (
        message.get("conversation")
        or (message.get("extendedTextMessage") or {}).get("text")
        or (message.get("imageMessage") or {}).get("caption")
        or ""
    )
    is_audio = "audioMessage" in message
    if not text.strip() and not is_audio:
        return None
    return InboundMessage(
        id=str(message_id),
        number=number,
        name=data.get("pushName"),
        text=text.strip(),
        is_audio=is_audio,
        raw=data,
    )


class WhatsAppSender(Protocol):
    async def send_text(self, number: str, text: str) -> None: ...

    async def send_audio(self, number: str, audio: bytes) -> None: ...

    async def typing(self, number: str) -> None: ...

    async def media_bytes(self, message: InboundMessage) -> bytes: ...


class EvolutionClient:
    """Minimal Evolution API v2 client (send text/audio, presence, media download)."""

    def __init__(self, base_url: str, api_key: str, instance: str, timeout: float = 30.0) -> None:
        self.instance = instance
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"), headers={"apikey": api_key}, timeout=timeout
        )

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        response = await self._http.post(f"{path}/{self.instance}", json=body)
        if response.status_code >= 400:
            log.error(
                "evolution.error", path=path, status=response.status_code, body=response.text[:300]
            )
            response.raise_for_status()
        result: dict[str, Any] = response.json() if response.content else {}
        return result

    async def send_text(self, number: str, text: str) -> None:
        await self._post("/message/sendText", {"number": number, "text": text})

    async def send_audio(self, number: str, audio: bytes) -> None:
        await self._post(
            "/message/sendWhatsAppAudio",
            {"number": number, "audio": base64.b64encode(audio).decode()},
        )

    async def typing(self, number: str) -> None:
        try:
            await self._post(
                "/chat/sendPresence", {"number": number, "presence": "composing", "delay": 3000}
            )
        except Exception as exc:  # presence is cosmetic
            log.debug("evolution.presence_failed", error=repr(exc))

    async def media_bytes(self, message: InboundMessage) -> bytes:
        inline = (message.raw.get("message") or {}).get("base64")
        if inline:
            return base64.b64decode(inline)
        result = await self._post(
            "/chat/getBase64FromMediaMessage",
            {"message": {"key": message.raw.get("key")}, "convertToMp4": False},
        )
        return base64.b64decode(result.get("base64", ""))

    async def aclose(self) -> None:
        await self._http.aclose()
