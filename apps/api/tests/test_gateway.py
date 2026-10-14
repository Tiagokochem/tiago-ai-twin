import pytest
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from tests.fakes import ScriptedProvider
from twin.llm.gateway import AllProvidersFailedError, LLMGateway
from twin.llm.usage import estimate_cost, track_usage


class Echo(BaseModel):
    text: str


MESSAGES = [HumanMessage("hi")]


async def test_structured_falls_back_to_secondary_provider() -> None:
    primary = ScriptedProvider("openai", fail=True)
    secondary = ScriptedProvider("deepseek", structured={"Echo": Echo(text="ok")})
    gateway = LLMGateway([primary, secondary])

    with track_usage() as usage:
        result = await gateway.structured("node", MESSAGES, Echo)

    assert result.text == "ok"
    assert [(c.provider, c.ok, c.fallback) for c in usage.calls] == [
        ("openai", False, False),
        ("deepseek", True, True),
    ]
    assert usage.used_fallback
    assert "ConnectionError" in (usage.calls[0].error or "")


async def test_stream_falls_back_before_first_token() -> None:
    gateway = LLMGateway(
        [ScriptedProvider("openai", fail=True), ScriptedProvider("deepseek", answer="hello world")]
    )

    with track_usage() as usage:
        tokens = [t async for t in gateway.stream("answer", MESSAGES)]

    assert "".join(tokens).strip() == "hello world"
    assert usage.calls[-1].output_tokens == 50


async def test_raises_when_every_provider_fails() -> None:
    gateway = LLMGateway([ScriptedProvider("a", fail=True), ScriptedProvider("b", fail=True)])

    with pytest.raises(AllProvidersFailedError, match="a: .*b: "):
        await gateway.structured("node", MESSAGES, Echo)


async def test_raises_without_providers() -> None:
    with pytest.raises(AllProvidersFailedError, match="no LLM provider"):
        [t async for t in LLMGateway([]).stream("answer", MESSAGES)]


def test_cost_estimate_handles_dated_model_names() -> None:
    assert estimate_cost("gpt-4.1-mini", 1_000_000, 0) == pytest.approx(0.40)
    assert estimate_cost("gpt-4.1-mini-2025-04-14", 0, 1_000_000) == pytest.approx(1.60)
    assert estimate_cost("unknown-model", 1000, 1000) == 0.0
