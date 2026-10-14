import json
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.fakes import FakeRetriever, FakeSpeech, ScriptedProvider, chunk
from twin.agent.graph import Analysis, Followups, Grade
from twin.channels.notify import HandoffEvent, SessionEndedEvent
from twin.config import Settings
from twin.container import Container, build_container
from twin.db.models import Base, ChatMessage, LLMCallRecord
from twin.llm.gateway import LLMGateway
from twin.main import create_app
from twin.observability.metrics import collect_metrics

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL not set"),
]


class RecordingNotifier:
    def __init__(self) -> None:
        self.handoffs: list[HandoffEvent] = []
        self.ended: list[SessionEndedEvent] = []

    async def handoff(self, event: HandoffEvent) -> None:
        self.handoffs.append(event)

    async def session_ended(self, event: SessionEndedEvent) -> None:
        self.ended.append(event)


def router(messages: Any) -> Analysis:
    question = str(messages[-1].content).lower()
    if "salary" in question:
        return Analysis(intent="handoff", lang="en", search_query="", handoff_reason="salary")
    return Analysis(intent="about_tiago", lang="en", search_query=question)


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
            "Followups": Followups(questions=["Which stack?"]),
        },
        answer="I built Nuvartis [1].",
    )
    settings = Settings(
        database_url=DATABASE_URL,
        admin_token=SecretStr("salt"),
        rate_limit_per_minute=5,
        whatsapp_owner_number="5545999990000",
    )
    built = build_container(
        settings,
        async_sessionmaker(engine, expire_on_commit=False),
        InMemorySaver(),
        gateway=LLMGateway([ScriptedProvider("broken", fail=True), provider]),
        retriever=FakeRetriever([chunk(1, "Nuvartis")]),
        notifier=RecordingNotifier(),
        speech=FakeSpeech(),
    )
    yield built
    await engine.dispose()


@pytest.fixture
async def client(container: Container) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(container=container)
    app.state.container = container
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def parse_sse(body: str) -> list[tuple[str, Any]]:
    events = []
    for block in body.replace("\r\n", "\n").split("\n\n"):
        name, data = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        if name:
            events.append((name, data))
    return events


async def ask(client: httpx.AsyncClient, session_id: str, message: str) -> list[tuple[str, Any]]:
    response = await client.post("/v1/chat", json={"session_id": session_id, "message": message})
    assert response.status_code == 200, response.text
    return parse_sse(response.text)


async def test_chat_streams_tokens_and_persists_metrics(
    client: httpx.AsyncClient, container: Container
) -> None:
    created = await client.post("/v1/sessions", json={"lang": "en"})
    assert created.status_code == 201
    body = created.json()
    assert body["starter_questions"] and "Tiago AI" in body["greeting"]

    events = await ask(client, body["session_id"], "Tell me about Nuvartis")

    names = [name for name, _ in events]
    assert names[0] == "status" and names[-2:] == ["final", "done"]
    answer = "".join(data for name, data in events if name == "token")
    assert answer.strip() == "I built Nuvartis [1]."
    final = dict(events)["final"]
    assert final["citations"][0]["title"] == "Nuvartis"
    assert final["followups"] == ["Which stack?"]
    done = dict(events)["done"]
    assert done["fallback"] is True and done["providers"] == ["openai"]

    sessionmaker = container.chat._sessionmaker
    async with sessionmaker() as db:
        roles = (await db.scalars(select(ChatMessage.role).order_by(ChatMessage.id))).all()
        calls = (await db.scalars(select(LLMCallRecord))).all()
    assert roles == ["user", "assistant"]
    assert {(c.provider, c.ok) for c in calls} == {("broken", False), ("openai", True)}

    detail = (await client.get(f"/v1/sessions/{body['session_id']}")).json()
    assert detail["messages"][1]["citations"][0]["n"] == 1

    transcript = await client.get(f"/v1/sessions/{body['session_id']}/transcript")
    assert "**Recruiter:**" in transcript.text and "[1] Nuvartis" in transcript.text


async def test_handoff_notifies_owner(client: httpx.AsyncClient, container: Container) -> None:
    session_id = (await client.post("/v1/sessions", json={"lang": "en"})).json()["session_id"]

    events = await ask(client, session_id, "What is your salary expectation?")
    await container.chat.drain()

    assert dict(events)["final"]["handoff"] == "salary"
    assert "wa.me/5545999990000" in "".join(d for n, d in events if n == "token")
    notifier = container.chat.notifier
    assert isinstance(notifier, RecordingNotifier)
    assert notifier.handoffs[0].reason == "salary"
    assert notifier.handoffs[0].question == "What is your salary expectation?"

    await client.post(f"/v1/sessions/{session_id}/end")
    await container.chat.drain()
    assert len(notifier.ended[0].transcript) == 2


async def test_unknown_session_and_rate_limit(client: httpx.AsyncClient) -> None:
    missing = await client.post(
        "/v1/chat",
        json={"session_id": "00000000-0000-0000-0000-000000000000", "message": "hi"},
    )
    assert missing.status_code == 404

    statuses = [(await client.post("/v1/sessions", json={})).status_code for _ in range(6)]
    assert statuses.count(429) >= 1


async def test_metrics_aggregate_turns_and_llm_calls(
    client: httpx.AsyncClient, container: Container
) -> None:
    session_id = (await client.post("/v1/sessions", json={"lang": "en"})).json()["session_id"]
    await ask(client, session_id, "Tell me about Nuvartis")
    await ask(client, session_id, "What is your salary expectation?")

    async with container.chat._sessionmaker() as db:
        metrics = await collect_metrics(db, days=1)

    assert metrics["overview"]["sessions"] == 1
    assert metrics["turns"]["turns"] == 2 and metrics["turns"]["handoffs"] == 1
    assert {i["intent"] for i in metrics["intents"]} == {"about_tiago", "handoff"}
    nodes = {n["node"]: n for n in metrics["nodes"]}
    assert nodes["answer"]["errors"] == 1  # the broken primary provider
    assert any(p["fallback_successes"] > 0 for p in metrics["providers"])


async def test_voice_transcribe_and_speak_stored_answer(
    client: httpx.AsyncClient, container: Container
) -> None:
    heard = await client.post(
        "/v1/voice/transcribe",
        files={"audio": ("q.webm", b"12345", "audio/webm")},
        data={"lang": "en"},
    )
    assert heard.json() == {"text": "heard 5 bytes in en"}

    session_id = (await client.post("/v1/sessions", json={"lang": "en"})).json()["session_id"]
    events = await ask(client, session_id, "Tell me about Nuvartis")
    message_id = dict(events)["done"]["message_id"]

    audio = await client.post(
        "/v1/voice/speak", json={"session_id": session_id, "message_id": message_id}
    )
    assert audio.status_code == 200 and audio.content == b"ID3audio"
    assert audio.headers["content-type"] == "audio/mpeg"
    speech = container.speech
    assert isinstance(speech, FakeSpeech)
    assert speech.spoken == ["I built Nuvartis."]

    wrong = await client.post(
        "/v1/voice/speak", json={"session_id": session_id, "message_id": message_id - 1}
    )
    assert wrong.status_code == 404


async def test_persona_endpoint(client: httpx.AsyncClient) -> None:
    body = (await client.get("/v1/persona")).json()

    assert body["contact_link"] == "https://wa.me/5545999990000"
    assert set(body["starter_questions"]) == {"pt", "en"}
