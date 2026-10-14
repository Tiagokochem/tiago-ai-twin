import secrets
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from twin.config import Settings, get_settings
from twin.container import Container
from twin.security.rate_limit import client_fingerprint

_bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def client_hash(request: Request, container: ContainerDep) -> str:
    settings = container.settings
    secret = settings.ip_hash_secret or settings.admin_token
    return client_fingerprint(client_ip(request), secret.get_secret_value() if secret else "twin")


def rate_limit(cost: int = 1) -> Callable[[Request, Container], Awaitable[None]]:
    """Per-client limit; expensive endpoints (LLM-heavy, speech) cost more."""

    async def dependency(request: Request, container: ContainerDep) -> None:
        retry_after = container.rate_limiter.hit(client_hash(request, container), cost)
        if retry_after is not None:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "too many requests",
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

    return dependency


rate_limited = rate_limit(1)


async def within_budget(container: ContainerDep) -> None:
    if await container.budget.exceeded():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "daily usage limit reached, please try again tomorrow",
            headers={"Retry-After": "3600"},
        )


def require_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    expected = settings.admin_token.get_secret_value() if settings.admin_token else ""
    if not expected:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "ADMIN_TOKEN not configured")
    if credentials is None or not secrets.compare_digest(credentials.credentials, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid admin token")
