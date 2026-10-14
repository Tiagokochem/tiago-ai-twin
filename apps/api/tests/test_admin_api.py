from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from twin.config import Settings, get_settings
from twin.main import app

TOKEN = "test-admin-token"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    settings = Settings(admin_token=SecretStr(TOKEN), openai_api_key=None)
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr("twin.rag.ingest.get_settings", lambda: settings)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_ingest_requires_admin_token(client: TestClient) -> None:
    assert client.post("/v1/admin/ingest").status_code == 401
    response = client.post("/v1/admin/ingest", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401


def test_ingest_without_openai_key_returns_503(client: TestClient) -> None:
    response = client.post("/v1/admin/ingest", headers={"Authorization": f"Bearer {TOKEN}"})

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
