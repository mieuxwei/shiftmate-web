from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI

from backend.app.api.v1.calendar import router
from backend.app.core.auth import AuthenticatedUser, get_current_user
from backend.app.core.settings import Settings, get_settings

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def calendar_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        UUID("00000000-0000-0000-0000-000000000706"), "authenticated"
    )
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="production",
        google_oauth_client_id="synthetic-client-id",
        google_oauth_client_secret="synthetic-client-secret",
        google_oauth_redirect_uri="https://shiftmate.test/api/v1/calendar/callback",
        google_oauth_state_secret="synthetic-state-secret-at-least-32-characters",
        calendar_token_encryption_key=(
            "synthetic-token-encryption-key-at-least-32-characters"
        ),
    )
    return app


async def test_connect_returns_pkce_authorization_url_and_secure_state_cookie() -> None:
    transport = httpx.ASGITransport(app=calendar_app())
    async with httpx.AsyncClient(
        transport=transport, base_url="https://shiftmate.test"
    ) as client:
        response = await client.get("/api/v1/calendar/connect")

    assert response.status_code == 200
    assert response.json()["authorization_url"].startswith(
        "https://accounts.google.com/o/oauth2/v2/auth?"
    )
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/api/v1/calendar/callback" in cookie


async def test_connect_rejects_external_return_redirect() -> None:
    transport = httpx.ASGITransport(app=calendar_app())
    async with httpx.AsyncClient(
        transport=transport, base_url="https://shiftmate.test"
    ) as client:
        response = await client.get(
            "/api/v1/calendar/connect",
            params={"return_path": "https://attacker.test/callback"},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "OAUTH_REDIRECT_INVALID"}
