from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import pytest

from backend.app.services.calendar_security import (
    GOOGLE_CALENDAR_EVENTS_SCOPE,
    CalendarSecurityError,
    OAuthStateManager,
    SecretBox,
    build_authorization_url,
    validate_return_path,
)

OWNER_ID = UUID("00000000-0000-0000-0000-000000000701")
SECRET = "synthetic-state-secret-with-at-least-32-characters"


def test_oauth_state_round_trip_binds_owner_state_pkce_and_return_path() -> None:
    now = datetime(2026, 9, 2, tzinfo=UTC)
    manager = OAuthStateManager(SECRET)
    cookie, issued = manager.issue(OWNER_ID, "/?calendar=connected", now)

    verified = manager.verify(cookie, issued.state, now + timedelta(minutes=9))
    query = parse_qs(
        urlparse(
            build_authorization_url("synthetic-client", "https://app.test/cb", issued)
        ).query
    )

    assert verified.owner_id == OWNER_ID
    assert verified.code_verifier == issued.code_verifier
    assert query["scope"] == [GOOGLE_CALENDAR_EVENTS_SCOPE]
    assert query["include_granted_scopes"] == ["true"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == [issued.state]


def test_oauth_state_rejects_mismatch_expiry_and_external_redirects() -> None:
    now = datetime(2026, 9, 2, tzinfo=UTC)
    manager = OAuthStateManager(SECRET)
    cookie, issued = manager.issue(OWNER_ID, "/", now)

    with pytest.raises(CalendarSecurityError, match="OAUTH_STATE_MISMATCH"):
        manager.verify(cookie, "attacker-state", now)
    with pytest.raises(CalendarSecurityError, match="OAUTH_STATE_EXPIRED"):
        manager.verify(cookie, issued.state, now + timedelta(minutes=11))
    for unsafe in ("https://attacker.test", "//attacker.test", "/ok#fragment"):
        with pytest.raises(CalendarSecurityError, match="OAUTH_REDIRECT_INVALID"):
            validate_return_path(unsafe)


def test_secret_box_encrypts_token_and_rejects_wrong_key() -> None:
    encrypted = SecretBox(SECRET).encrypt("synthetic-refresh-token")

    assert "synthetic-refresh-token" not in encrypted
    assert SecretBox(SECRET).decrypt(encrypted) == "synthetic-refresh-token"
    with pytest.raises(CalendarSecurityError, match="CALENDAR_TOKEN_INVALID"):
        SecretBox("different-synthetic-secret-with-32-characters").decrypt(encrypted)
