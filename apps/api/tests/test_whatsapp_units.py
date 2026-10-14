from typing import Any

from tests.fakes import FakeSender
from twin.channels.evolution import parse_webhook
from twin.channels.notify import HandoffEvent, SessionEndedEvent
from twin.channels.whatsapp import WhatsAppNotifier, format_for_whatsapp


def upsert(message: dict[str, Any], **key: Any) -> dict[str, Any]:
    return {
        "event": "messages.upsert",
        "instance": "twin",
        "data": {
            "key": {
                "remoteJid": "5511988887777@s.whatsapp.net",
                "fromMe": False,
                "id": "ABC",
                **key,
            },
            "pushName": "Ana",
            "message": message,
        },
    }


def test_parse_text_and_extended_text() -> None:
    parsed = parse_webhook(upsert({"conversation": " Olá "}))
    assert parsed and parsed.number == "5511988887777" and parsed.text == "Olá"
    assert parsed.name == "Ana" and not parsed.is_audio

    extended = parse_webhook(upsert({"extendedTextMessage": {"text": "link http://x"}}))
    assert extended and extended.text == "link http://x"


def test_parse_audio_and_lid_addressing() -> None:
    audio = parse_webhook(
        upsert(
            {"audioMessage": {"seconds": 4}},
            remoteJid="123@lid",
            senderPn="5545911112222@s.whatsapp.net",
        )
    )
    assert audio and audio.is_audio and audio.number == "5545911112222"


def test_parse_ignores_own_group_and_other_events() -> None:
    assert parse_webhook(upsert({"conversation": "x"}, fromMe=True)) is None
    assert parse_webhook(upsert({"conversation": "x"}, remoteJid="123-456@g.us")) is None
    assert parse_webhook(upsert({"stickerMessage": {}})) is None
    assert parse_webhook({"event": "connection.update", "data": {}}) is None
    assert parse_webhook(
        {"event": "MESSAGES_UPSERT", "data": upsert({"conversation": "hi"})["data"]}
    )


def test_format_for_whatsapp() -> None:
    text = "## Stack\nI use **Laravel** [1] and Python [2][1]."
    citations = [
        {"n": 1, "title": "Skills", "url": None},
        {"n": 2, "title": "Nuvartis", "url": "https://nuvartis.com"},
    ]
    assert format_for_whatsapp(text, citations, "en") == (
        "Stack\nI use *Laravel* and Python.\n\n_Sources:_\n• Skills\n• Nuvartis - https://nuvartis.com"
    )


async def test_notifier_formats_handoff_and_summary() -> None:
    sender = FakeSender()
    notifier = WhatsAppNotifier(sender, "5545999990000", "https://1-2-3-4.sslip.io/")
    await notifier.handoff(
        HandoffEvent(
            session_id="s1",
            channel="whatsapp",
            lang="pt",
            reason="salary",
            question="Qual sua pretensão?",
            transcript=[("user", "Qual sua pretensão?")],
            contact="5511988887777",
        )
    )
    await notifier.session_ended(
        SessionEndedEvent(
            session_id="s1", channel="web", lang="en", transcript=[("assistant", "hi")]
        )
    )
    await notifier.session_ended(
        SessionEndedEvent(
            session_id="s2",
            channel="web",
            lang="en",
            transcript=[("user", "Stack?"), ("assistant", "...")],
        )
    )

    assert [n for n, _ in sender.texts] == ["5545999990000", "5545999990000"]
    handoff = sender.texts[0][1]
    assert "pretensão salarial" in handoff and "https://wa.me/5511988887777" in handoff
    assert "https://1-2-3-4.sslip.io/api/v1/sessions/s1/transcript" in handoff
    assert "1. Stack?" in sender.texts[1][1]
