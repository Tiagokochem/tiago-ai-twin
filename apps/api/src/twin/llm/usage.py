from collections.abc import Iterator
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from dataclasses import dataclass, field

# USD per 1M tokens (input, output). Approximate list prices; override by
# editing this table. Unknown models are counted as zero cost.
PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "deepseek-chat": (0.27, 1.10),
    "gpt-4o-transcribe": (2.50, 10.00),
    "gpt-4o-mini-transcribe": (1.25, 5.00),
    "gpt-4o-mini-tts": (0.60, 12.00),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICES_PER_MILLION.get(model)
    if price is None:
        # Dated snapshots like "gpt-4.1-mini-2025-04-14" share the base price.
        price = next(
            (
                p
                for name, p in sorted(PRICES_PER_MILLION.items(), key=lambda i: -len(i[0]))
                if model.startswith(name)
            ),
            (0.0, 0.0),
        )
    return (input_tokens * price[0] + output_tokens * price[1]) / 1_000_000


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class LLMCall:
    node: str
    provider: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    ok: bool
    fallback: bool = False
    error: str | None = None


@dataclass
class UsageTracker:
    calls: list[LLMCall] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(c.input_tokens + c.output_tokens for c in self.calls)

    @property
    def total_cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    @property
    def used_fallback(self) -> bool:
        return any(c.fallback and c.ok for c in self.calls)

    def summary(self) -> dict[str, object]:
        return {
            "llm_calls": len(self.calls),
            "tokens": self.total_tokens,
            "cost_usd": round(self.total_cost_usd, 6),
            "providers": sorted({c.provider for c in self.calls if c.ok}),
            "fallback": self.used_fallback,
        }


_current: ContextVar[UsageTracker | None] = ContextVar("usage_tracker", default=None)


@contextmanager
def track_usage() -> Iterator[UsageTracker]:
    tracker = UsageTracker()
    token = _current.set(tracker)
    try:
        yield tracker
    finally:
        # An async generator may be finalized from another context (e.g. client
        # disconnect); resetting there raises ValueError and is safe to skip.
        with suppress(ValueError):
            _current.reset(token)


def record_call(call: LLMCall) -> None:
    tracker = _current.get()
    if tracker is not None:
        tracker.calls.append(call)
