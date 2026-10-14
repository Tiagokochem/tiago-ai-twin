import secrets
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
    salt = (
        container.settings.admin_token.get_secret_value() if container.settings.admin_token else ""
    )
    return client_fingerprint(client_ip(request), salt or "twin")


def rate_limited(request: Request, container: ContainerDep) -> None:
    retry_after = container.rate_limiter.hit(client_hash(request, container))
    if retry_after is not None:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "too many requests",
            headers={"Retry-After": str(int(retry_after) + 1)},
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
