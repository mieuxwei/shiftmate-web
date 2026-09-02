from typing import Protocol
from uuid import UUID

import anyio
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier

from backend.app.core.auth import (
    AuthenticatedUser,
    InvalidAccessToken,
    build_verifier,
)
from backend.app.core.settings import Settings

READ_SCOPE = "shiftmate:read"


class McpAuthenticationError(Exception):
    pass


class PrincipalProvider(Protocol):
    async def require_user(self) -> AuthenticatedUser: ...


class SupabaseMcpTokenVerifier:
    """Adapt the existing Supabase JWT verifier to MCP bearer authentication."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def verify_token(self, token: str) -> AccessToken | None:
        if self.settings.supabase_url is None:
            return None
        verifier = build_verifier(
            str(self.settings.supabase_url), self.settings.supabase_jwt_audience
        )
        try:
            user = await anyio.to_thread.run_sync(verifier.verify, token)
        except InvalidAccessToken:
            return None
        issuer = f"{str(self.settings.supabase_url).rstrip('/')}/auth/v1"
        return AccessToken(
            token=token,
            client_id="shiftmate-web",
            scopes=[READ_SCOPE],
            subject=str(user.id),
            claims={"iss": issuer, "role": user.role},
        )


class TransportPrincipalProvider:
    """Resolve identity from HTTP context or a verified stdio process token."""

    def __init__(
        self,
        token_verifier: TokenVerifier,
        stdio_access_token: str | None = None,
    ) -> None:
        self.token_verifier = token_verifier
        self.stdio_access_token = stdio_access_token

    async def require_user(self) -> AuthenticatedUser:
        access_token = get_access_token()
        if access_token is None and self.stdio_access_token:
            access_token = await self.token_verifier.verify_token(
                self.stdio_access_token
            )
        if (
            access_token is None
            or READ_SCOPE not in access_token.scopes
            or access_token.subject is None
        ):
            raise McpAuthenticationError
        try:
            return AuthenticatedUser(
                id=UUID(access_token.subject), role="authenticated"
            )
        except ValueError as error:
            raise McpAuthenticationError from error
