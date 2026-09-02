from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Protocol
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWK, PyJWKClient
from jwt.exceptions import PyJWTError

from backend.app.core.settings import Settings, get_settings

ASYMMETRIC_ALGORITHMS = ["ES256", "RS256", "EdDSA"]
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: UUID
    role: str


class SigningKeyClient(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> PyJWK: ...


class SupabaseJwtVerifier:
    def __init__(
        self, issuer: str, audience: str, jwks_client: SigningKeyClient
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.jwks_client = jwks_client

    def verify(self, token: str) -> AuthenticatedUser:
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=ASYMMETRIC_ALGORITHMS,
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "sub", "aud", "iss", "role"]},
            )
            role = claims["role"]
            if role != "authenticated":
                raise ValueError("Only authenticated user tokens are accepted")
            return AuthenticatedUser(id=UUID(claims["sub"]), role=role)
        except (KeyError, TypeError, ValueError, PyJWTError) as exc:
            raise InvalidAccessToken from exc


class InvalidAccessToken(Exception):
    pass


@lru_cache
def build_verifier(supabase_url: str, audience: str) -> SupabaseJwtVerifier:
    issuer = f"{supabase_url.rstrip('/')}/auth/v1"
    client = PyJWKClient(f"{issuer}/.well-known/jwks.json", lifespan=600)
    return SupabaseJwtVerifier(issuer, audience, client)


def get_jwt_verifier(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SupabaseJwtVerifier:
    if settings.supabase_url is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )
    return build_verifier(str(settings.supabase_url), settings.supabase_jwt_audience)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    verifier: Annotated[SupabaseJwtVerifier, Depends(get_jwt_verifier)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verifier.verify(credentials.credentials)
    except InvalidAccessToken as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
