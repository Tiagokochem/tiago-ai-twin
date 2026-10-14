import asyncio
import time
from collections.abc import AsyncIterator, Sequence

import structlog
from langchain_core.messages import BaseMessage

from twin.llm.providers import ChatProvider, SchemaT, Tier
from twin.llm.usage import LLMCall, TokenUsage, estimate_cost, record_call

log = structlog.get_logger()


class AllProvidersFailedError(RuntimeError):
    pass


class LLMGateway:
    """Calls providers in priority order and falls back on any failure.

    Every attempt (successful or not) is recorded with node, provider,
    latency, tokens and cost, so fallbacks are visible in metrics.
    Streams only fall back if the failure happens before the first token.
    """

    def __init__(self, providers: Sequence[ChatProvider], timeout_seconds: float = 30.0) -> None:
        self.providers = list(providers)
        self.timeout_seconds = timeout_seconds

    @property
    def available(self) -> bool:
        return bool(self.providers)

    async def structured(
        self,
        node: str,
        messages: Sequence[BaseMessage],
        schema: type[SchemaT],
        tier: Tier = "fast",
        prompt: str | None = None,
    ) -> SchemaT:
        errors: list[str] = []
        for index, provider in enumerate(self.providers):
            started = time.perf_counter()
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    result, usage = await provider.structured(messages, schema, tier)
            except Exception as exc:
                self._record(node, provider, tier, started, TokenUsage(), index, prompt, exc)
                errors.append(f"{provider.name}: {exc!r}")
                continue
            self._record(node, provider, tier, started, usage, index, prompt)
            return result
        raise AllProvidersFailedError("; ".join(errors) or "no LLM provider configured")

    async def stream(
        self,
        node: str,
        messages: Sequence[BaseMessage],
        tier: Tier = "answer",
        prompt: str | None = None,
    ) -> AsyncIterator[str]:
        errors: list[str] = []
        for index, provider in enumerate(self.providers):
            started = time.perf_counter()
            usage = TokenUsage()
            emitted = False
            try:
                async with asyncio.timeout(self.timeout_seconds * 2):
                    async for item in provider.stream(messages, tier):
                        if isinstance(item, TokenUsage):
                            usage = item
                            continue
                        emitted = True
                        yield item
            except Exception as exc:
                self._record(node, provider, tier, started, usage, index, prompt, exc)
                if emitted:
                    raise
                errors.append(f"{provider.name}: {exc!r}")
                continue
            self._record(node, provider, tier, started, usage, index, prompt)
            return
        raise AllProvidersFailedError("; ".join(errors) or "no LLM provider configured")

    @staticmethod
    def _record(
        node: str,
        provider: ChatProvider,
        tier: Tier,
        started: float,
        usage: TokenUsage,
        index: int,
        prompt: str | None = None,
        error: BaseException | None = None,
    ) -> None:
        model = provider.model_name(tier)
        call = LLMCall(
            node=node,
            provider=provider.name,
            model=model,
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=estimate_cost(model, usage.input_tokens, usage.output_tokens),
            ok=error is None,
            fallback=index > 0,
            error=repr(error)[:500] if error else None,
            prompt=prompt,
        )
        record_call(call)
        if error is None:
            log.info("llm.call", **{k: v for k, v in call.__dict__.items() if k != "error"})
        else:
            log.warning("llm.call_failed", node=node, provider=provider.name, error=call.error)
