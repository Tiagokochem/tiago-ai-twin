from twin.logging import redact
from twin.security.rate_limit import RateLimiter


def test_redact_masks_contacts_but_not_dates_or_ids() -> None:
    text = "from +55 45 99999-0000 <a.b+c@mail.com> on 2026-10-14, session 1234"
    assert redact(text) == "from <phone …0000> <<email>> on 2026-10-14, session 1234"


def test_rate_limiter_weights_requests_by_cost() -> None:
    now = [0.0]
    limiter = RateLimiter(per_minute=5, per_day=8, clock=lambda: now[0])
    assert limiter.hit("a", cost=4) is None
    assert limiter.hit("a", cost=2) is not None  # 6 > 5 per minute
    assert limiter.hit("a") is None
    now[0] = 61
    assert limiter.hit("a", cost=4) is not None  # 9 > 8 per day
    assert limiter.hit("a", cost=3) is None
    assert limiter.hit("b", cost=6) is not None  # a single request above the minute cap
