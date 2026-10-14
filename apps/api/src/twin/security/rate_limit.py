import hashlib
import time
from collections import deque
from collections.abc import Callable

MINUTE = 60.0
DAY = 86_400.0


class RateLimiter:
    """In-memory sliding-window limiter (per minute and per day).

    Good enough for a single API instance; swap for Redis when scaling out.
    """

    def __init__(
        self, per_minute: int, per_day: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._per_minute = per_minute
        self._per_day = per_day
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str, cost: int = 1) -> float | None:
        """Register a request worth `cost` hits (expensive endpoints cost
        more). Returns None if allowed, else seconds to wait."""
        now = self._clock()
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= DAY:
            hits.popleft()

        last_minute = sum(1 for t in hits if now - t < MINUTE)
        if last_minute + cost > self._per_minute:
            oldest = next((t for t in hits if now - t < MINUTE), now)
            return MINUTE - (now - oldest)
        if len(hits) + cost > self._per_day:
            return DAY - (now - hits[0]) if hits else DAY

        hits.extend([now] * cost)
        if len(self._hits) > 10_000:
            self._evict(now)
        return None

    def _evict(self, now: float) -> None:
        for key in [k for k, v in self._hits.items() if not v or now - v[-1] >= DAY]:
            del self._hits[key]


def client_fingerprint(ip: str, salt: str) -> str:
    """Store a salted hash instead of the raw IP address."""
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()
