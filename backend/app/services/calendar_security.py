import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlparse
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken

GOOGLE_CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events.owned"
STATE_TTL = timedelta(minutes=10)


class CalendarSecurityError(ValueError):
    """Raised when OAuth state or encrypted token material is invalid."""


@dataclass(frozen=True, slots=True)
class OAuthState:
    owner_id: UUID
    state: str
    code_verifier: str
    return_path: str


class SecretBox:
    def __init__(self, secret: str) -> None:
        if len(secret) < 32:
            raise CalendarSecurityError("CALENDAR_SECRET_TOO_SHORT")
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except (InvalidToken, ValueError) as error:
            raise CalendarSecurityError("CALENDAR_TOKEN_INVALID") from error


class OAuthStateManager:
    def __init__(self, secret: str) -> None:
        self._box = SecretBox(secret)

    def issue(
        self,
        owner_id: UUID,
        return_path: str = "/?calendar=connected",
        now: datetime | None = None,
    ) -> tuple[str, OAuthState]:
        safe_path = validate_return_path(return_path)
        issued_at = now or datetime.now(UTC)
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        payload = json.dumps(
            {
                "owner_id": str(owner_id),
                "state": state,
                "code_verifier": verifier,
                "return_path": safe_path,
                "issued_at": int(issued_at.timestamp()),
            },
            separators=(",", ":"),
        )
        return self._box.encrypt(payload), OAuthState(
            owner_id=owner_id,
            state=state,
            code_verifier=verifier,
            return_path=safe_path,
        )

    def verify(
        self, cookie: str, returned_state: str, now: datetime | None = None
    ) -> OAuthState:
        try:
            payload = json.loads(self._box.decrypt(cookie))
            issued_at = datetime.fromtimestamp(payload["issued_at"], tz=UTC)
            owner_id = UUID(payload["owner_id"])
            state = str(payload["state"])
            verifier = str(payload["code_verifier"])
            return_path = validate_return_path(str(payload["return_path"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise CalendarSecurityError("OAUTH_STATE_INVALID") from error
        current = now or datetime.now(UTC)
        if current < issued_at or current - issued_at > STATE_TTL:
            raise CalendarSecurityError("OAUTH_STATE_EXPIRED")
        if not secrets.compare_digest(state, returned_state):
            raise CalendarSecurityError("OAUTH_STATE_MISMATCH")
        return OAuthState(owner_id, state, verifier, return_path)


def build_authorization_url(
    client_id: str, redirect_uri: str, state: OAuthState
) -> str:
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(state.code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GOOGLE_CALENDAR_EVENTS_SCOPE,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state.state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


def validate_return_path(value: str) -> str:
    parsed = urlparse(value)
    if not value.startswith("/") or value.startswith("//"):
        raise CalendarSecurityError("OAUTH_REDIRECT_INVALID")
    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise CalendarSecurityError("OAUTH_REDIRECT_INVALID")
    return value
