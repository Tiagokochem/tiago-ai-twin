from collections.abc import AsyncIterator, Sequence
from typing import Literal, Protocol, TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from twin.config import Settings
from twin.llm.usage import TokenUsage

Tier = Literal["fast", "answer"]

# Output caps per tier: structured calls are short; answers are skimmed by
# recruiters, and a long job-fit report still fits comfortably.
FAST_MAX_TOKENS = 500
ANSWER_MAX_TOKENS = 1200
SchemaT = TypeVar("SchemaT", bound=BaseModel)


class StructuredOutputError(RuntimeError):
    pass


class ChatProvider(Protocol):
    name: str

    def model_name(self, tier: Tier) -> str: ...

    async def structured(
        self, messages: Sequence[BaseMessage], schema: type[SchemaT], tier: Tier
    ) -> tuple[SchemaT, TokenUsage]: ...

    def stream(
        self, messages: Sequence[BaseMessage], tier: Tier
    ) -> AsyncIterator[str | TokenUsage]: ...


def _usage(message: BaseMessage | None) -> TokenUsage:
    meta = getattr(message, "usage_metadata", None) or {}
    return TokenUsage(meta.get("input_tokens", 0), meta.get("output_tokens", 0))


class LangChainProvider:
    """Wraps LangChain chat models (one per tier) behind ChatProvider."""

    def __init__(self, name: str, models: dict[Tier, BaseChatModel]) -> None:
        self.name = name
        self._models = models

    def model_name(self, tier: Tier) -> str:
        model = self._models[tier]
        return str(getattr(model, "model_name", None) or getattr(model, "model", "unknown"))

    async def structured(
        self, messages: Sequence[BaseMessage], schema: type[SchemaT], tier: Tier
    ) -> tuple[SchemaT, TokenUsage]:
        runnable = self._models[tier].with_structured_output(
            schema, method="function_calling", include_raw=True
        )
        result = await runnable.ainvoke(list(messages))
        assert isinstance(result, dict)
        parsed = result.get("parsed")
        if not isinstance(parsed, schema):
            raise StructuredOutputError(f"{self.name}: {result.get('parsing_error')}")
        return parsed, _usage(result.get("raw"))

    async def stream(
        self, messages: Sequence[BaseMessage], tier: Tier
    ) -> AsyncIterator[str | TokenUsage]:
        usage = TokenUsage()
        async for chunk in self._models[tier].astream(list(messages)):
            if isinstance(chunk.content, str) and chunk.content:
                yield chunk.content
            if isinstance(chunk, AIMessage) and chunk.usage_metadata:
                usage = _usage(chunk)
        yield usage


def build_providers(settings: Settings) -> list[ChatProvider]:
    timeout = settings.llm_timeout_seconds
    providers: list[ChatProvider] = []
    if settings.openai_api_key and settings.openai_api_key.get_secret_value():
        key = settings.openai_api_key

        def openai(model: str, temperature: float, max_tokens: int) -> ChatOpenAI:
            return ChatOpenAI(
                model=model,
                api_key=key,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                max_retries=1,
                stream_usage=True,
            )

        providers.append(
            LangChainProvider(
                "openai",
                {
                    "fast": openai(settings.openai_fast_model, 0.0, FAST_MAX_TOKENS),
                    "answer": openai(settings.openai_model, 0.3, ANSWER_MAX_TOKENS),
                },
            )
        )
    if settings.deepseek_api_key and settings.deepseek_api_key.get_secret_value():
        key = settings.deepseek_api_key

        def deepseek(temperature: float, max_tokens: int) -> ChatOpenAI:
            return ChatOpenAI(
                model=settings.deepseek_model,
                api_key=key,
                base_url=settings.deepseek_base_url,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                max_retries=1,
                stream_usage=True,
            )

        providers.append(
            LangChainProvider(
                "deepseek",
                {
                    "fast": deepseek(0.0, FAST_MAX_TOKENS),
                    "answer": deepseek(0.3, ANSWER_MAX_TOKENS),
                },
            )
        )
    return providers
