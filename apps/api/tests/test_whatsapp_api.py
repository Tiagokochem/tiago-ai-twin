import os
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import httpx
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.fakes import FakeRetriever, FakeSender, FakeSpeech, ScriptedProvider, chunk
from twin.agent.graph import Analysis, Followups, Grade
from twin.config import Settings
from twin.container import Container, build_container
from twin.db.models import Base, ChatSession
from twin.llm.gateway import LLMGateway
from twin.main import create_app

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
OWNER = "5545999990000"
RECRUITER = "5511988887777"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL not set"),
]


def router(messages: Any) -> Analysis:
    question = str(messages[-1].content).lower()
    if "salário" in question:
        return Analysis(intent="handoff", lang="pt", search_query="", handoff_reason="salary")
    return Analysis(intent="about_tiago", lang="pt", search_query=question)


@pytest.fixture
async def container() -> AsyncIterator[Container]:
    assert DATABASE_URL
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    provider = ScriptedProvider(
        "openai",
        structured={
            "Analysis": router,
            "Grade": Grade(relevant_ids=[0]),
            "Followups": Followups(questions=["unused"]),
        },
        answer=lambda messages: f"Uso **Laravel** [1]. Pergunta: {messages[-1].content}",
    )
    settings = Settings(
        database_url=DATABASE_URL,
        admin_token=SecretStr("salt"),
        whatsapp_owner_number=OWNER,
        evolution_webhook_token=SecretStr("hook-secret"),
        evolution_instance="twin",
        whatsapp_debounce_seconds=0.05,
        whatsapp_rate_per_minute=3,
        public_url="https://1-2-3-4.sslip.io",
    )
    built = build_container(
        settings,
        async_sessionmaker(engine, expire_on_commit=False),
        InMemorySaver(),
        gateway=LLMGateway([provider]),
        retriever=FakeRetriever([chunk(1, "Skills")]),
        speech=FakeSpeech(),
        whatsapp_sender=FakeSender(),
    )
    yield built
    await engine.dispose()


@pytest.fixture
async def client(container: Container) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(container=container)
    app.state.container = container
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


def event(message_id: str, message: dict[str, Any], number: str = RECRUITER) -> dict[str, Any]:
    return {
        "event": "messages.upsert",
        "instance": "twin",
        "data": {
            "key": {"remoteJid": f"{number}@s.whatsapp.net", "fromMe": False, "id": message_id},
            "pushName": "Ana",
            "message": message,
        },
    }


async def post(client: httpx.AsyncClient, payload: dict[str, Any]) -> str:
    response = await client.post("/v1/channels/whatsapp?token=hook-secret", json=payload)
    assert response.status_code == 200, response.text
    return str(response.json()["status"])


def sender(container: Container) -> FakeSender:
    assert container.whatsapp is not None
    fake = container.whatsapp.sender
    assert isinstance(fake, FakeSender)
    return fake


async def settle(container: Container) -> None:
    assert container.whatsapp is not None
    await container.whatsapp.drain()
    await container.chat.drain()


async def test_webhook_rejects_bad_token(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/v1/channels/whatsapp?token=nope", json=event("1", {"conversation": "oi"})
    )
    assert response.status_code == 401


async def test_debounced_messages_become_one_turn_with_sources(
    client: httpx.AsyncClient, container: Container
) -> None:
    assert await post(client, event("m1", {"conversation": "Oi!"})) == "queued"
    assert await post(client, event("m2", {"conversation": "Qual sua stack?"})) == "queued"
    assert await post(client, event("m2", {"conversation": "Qual sua stack?"})) == "duplicate"
    await settle(container)

    texts = sender(container).to(RECRUITER)
    assert len(texts) == 2
    assert "Tiago AI" in texts[0] and f"wa.me/{OWNER}" in texts[0]  # welcome
    assert texts[1].startswith("Uso *Laravel*. Pergunta: Oi!\nQual sua stack?")
    assert "_Fontes:_\n• Skills" in texts[1]


async def test_audio_is_transcribed_and_answered_with_voice(
    client: httpx.AsyncClient, container: Container
) -> None:
    await post(client, event("a1", {"audioMessage": {"seconds": 3}}))
    await settle(container)

    fake = sender(container)
    assert "Pergunta: heard 3 bytes in pt" in fake.to(RECRUITER)[-1]
    assert fake.audios == [(RECRUITER, b"ID3audio")]


async def test_handoff_and_human_command_notify_owner(
    client: httpx.AsyncClient, container: Container
) -> None:
    await post(client, event("h1", {"conversation": "Qual sua pretensão de salário?"}))
    await settle(container)
    await post(client, event("h2", {"conversation": "/humano"}))
    await settle(container)

    fake = sender(container)
    owner = fake.to(OWNER)
    assert len(owner) == 2
    assert "pretensão salarial" in owner[0] and f"https://wa.me/{RECRUITER}" in owner[0]
    assert "pediu para falar com você" in owner[1]
    assert "WhatsApp pessoal" in fake.to(RECRUITER)[-1]


async def test_reset_rate_limit_and_idle_summary(
    client: httpx.AsyncClient, container: Container
) -> None:
    await post(client, event("r1", {"conversation": "Stack?"}))
    await settle(container)
    await post(client, event("r2", {"conversation": "/novo"}))
    await settle(container)
    fake = sender(container)
    assert fake.to(RECRUITER)[-1] == "Conversa reiniciada. Pode perguntar!"
    assert "resumo da entrevista" in fake.to(OWNER)[-1]  # the first session was closed

    await post(client, event("r3", {"conversation": "Projetos?"}))
    await settle(container)
    await post(client, event("r4", {"conversation": "Mais?"}))
    await settle(container)
    assert fake.to(RECRUITER)[-1].startswith("Recebi muitas mensagens")

    async with container.chat._sessionmaker() as db:
        await db.execute(
            update(ChatSession).values(
                last_activity_at=ChatSession.last_activity_at - timedelta(hours=3)
            )
        )
        await db.commit()
    assert await container.chat.end_idle_sessions(timedelta(minutes=90)) == 1
    await container.chat.drain()
    assert "1. Projetos?" in fake.to(OWNER)[-1]
