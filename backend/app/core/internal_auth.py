from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Protocol

import jwt
from fastapi import Depends, HTTPException, Request, status
from jwt import PyJWK, PyJWKClient
from jwt.exceptions import PyJWTError

from backend.app.core.settings import Settings, get_settings

GOOGLE_OIDC_ISSUERS = ("https://accounts.google.com", "accounts.google.com")


class SigningKeyClient(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> PyJWK: ...


@dataclass(frozen=True, slots=True)
class SchedulerPrincipal:
    email: str


class SchedulerOidcVerifier:
    def __init__(
        self, audience: str, service_account_email: str, keys: SigningKeyClient
    ) -> None:
        self.audience = audience
        self.service_account_email = service_account_email.casefold()
        self.keys = keys

    def verify(self, token: str) -> SchedulerPrincipal:
        try:
            key = self.keys.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["RS256"],
                audience=self.audience,
                options={"require": ["aud", "exp", "iat", "iss", "email"]},
            )
            if claims["iss"] not in GOOGLE_OIDC_ISSUERS:
                raise ValueError("issuer")
            email = str(claims["email"]).casefold()
            if (
                email != self.service_account_email
                or claims.get("email_verified") is not True
            ):
                raise ValueError("principal")
            return SchedulerPrincipal(email)
        except (KeyError, TypeError, ValueError, PyJWTError) as error:
            raise InvalidSchedulerToken from error


class InvalidSchedulerToken(Exception):
    pass


@lru_cache
def build_scheduler_verifier(
    audience: str, service_account_email: str
) -> SchedulerOidcVerifier:
    return SchedulerOidcVerifier(
        audience,
        service_account_email,
        PyJWKClient("https://www.googleapis.com/oauth2/v3/certs", lifespan=3600),
    )


def get_scheduler_verifier(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SchedulerOidcVerifier:
    if (
        not settings.scheduler_oidc_audience
        or not settings.scheduler_service_account_email
    ):
        raise HTTPException(status_code=401, detail="SCHEDULER_UNAUTHORIZED")
    return build_scheduler_verifier(
        settings.scheduler_oidc_audience, settings.scheduler_service_account_email
    )


def require_scheduler_principal(
    request: Request,
    verifier: Annotated[SchedulerOidcVerifier, Depends(get_scheduler_verifier)],
) -> SchedulerPrincipal:
    header = request.headers.get("x-serverless-authorization") or request.headers.get(
        "authorization"
    )
    if not header or not header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SCHEDULER_UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verifier.verify(header.split(" ", 1)[1])
    except InvalidSchedulerToken as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SCHEDULER_UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
