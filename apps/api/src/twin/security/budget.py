import time
from collections.abc import Callable
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from twin.db.models import LLMCallRecord

log = structlog.get_logger()


class BudgetGuard:
    """Daily spend circuit breaker. Sums today's recorded LLM cost (chat
    turns and job fit) and blocks new expensive work once the cap is hit, so
    a scripted abuse wave cannot run up the API bill."""

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        daily_usd: float,
        cache_seconds: float = 30,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._sessionmaker = sessionmaker
        self.daily_usd = daily_usd
        self._cache_seconds = cache_seconds
        self._clock = clock
        self._checked_at = float("-inf")
        self._spent = 0.0

    async def spent_today(self) -> float:
        now = self._clock()
        if now - self._checked_at >= self._cache_seconds:
            midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            async with self._sessionmaker() as db:
                total = await db.scalar(
                    select(func.coalesce(func.sum(LLMCallRecord.cost_usd), 0.0)).where(
                        LLMCallRecord.created_at >= midnight
                    )
                )
            self._spent = float(total or 0.0)
            self._checked_at = now
        return self._spent

    async def exceeded(self) -> bool:
        if self.daily_usd <= 0:
            return False
        spent = await self.spent_today()
        if spent >= self.daily_usd:
            log.error("budget.exceeded", spent_usd=round(spent, 4), cap_usd=self.daily_usd)
            return True
        return False
