from uuid import UUID

import pytest

from backend.app.core.auth import AuthenticatedUser, InvalidAccessToken
from backend.app.core.settings import Settings
from backend.app.mcp import auth as auth_module
from backend.app.mcp.auth import (
    McpAuthenticationError,
    SupabaseMcpTokenVerifier,
    TransportPrincipalProvider,
)

pytestmark = pytest.mark.anyio
USER_ID = UUID("00000000-0000-0000-0000-000000000802")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class SyntheticJwtVerifier:
    def verify(self, token: str) -> AuthenticatedUser:
        if token != "synthetic-valid-token":
            raise InvalidAccessToken
        return AuthenticatedUser(USER_ID, "authenticated")


async def test_supabase_adapter_and_stdio_provider_share_verified_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_module,
        "build_verifier",
        lambda url, audience: SyntheticJwtVerifier(),
    )
    verifier = SupabaseMcpTokenVerifier(
        Settings(supabase_url="https://synthetic.supabase.co")
    )

    access = await verifier.verify_token("synthetic-valid-token")
    user = await TransportPrincipalProvider(
        verifier, "synthetic-valid-token"
    ).require_user()

    assert access is not None
    assert access.subject == str(USER_ID)
    assert access.scopes == ["shiftmate:read"]
    assert access.claims == {
        "iss": "https://synthetic.supabase.co/auth/v1",
        "role": "authenticated",
    }
    assert user == AuthenticatedUser(USER_ID, "authenticated")


async def test_stdio_provider_rejects_missing_and_invalid_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_module,
        "build_verifier",
        lambda url, audience: SyntheticJwtVerifier(),
    )
    verifier = SupabaseMcpTokenVerifier(
        Settings(supabase_url="https://synthetic.supabase.co")
    )

    assert await verifier.verify_token("invalid") is None
    with pytest.raises(McpAuthenticationError):
        await TransportPrincipalProvider(verifier).require_user()
    with pytest.raises(McpAuthenticationError):
        await TransportPrincipalProvider(verifier, "invalid").require_user()
