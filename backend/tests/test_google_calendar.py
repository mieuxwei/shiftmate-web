import json

import httpx
import pytest

from backend.app.integrations.google_calendar import (
    GoogleCalendarClient,
    GoogleTokenRevokedError,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def client(handler: httpx.MockTransport) -> GoogleCalendarClient:
    return GoogleCalendarClient(
        "synthetic-client",
        "synthetic-secret",
        "https://shiftmate.test/api/v1/calendar/callback",
        5,
        transport=handler,
    )


async def test_refresh_maps_invalid_grant_to_revoked_state() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            400, json={"error": "invalid_grant"}, request=request
        )
    )

    with pytest.raises(GoogleTokenRevokedError, match="CALENDAR_AUTH_REVOKED"):
        await client(transport).refresh("synthetic-refresh-token")


async def test_event_create_conflict_updates_same_external_id() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        status_code = 409 if request.method == "POST" else 200
        return httpx.Response(status_code, json={}, request=request)

    await client(httpx.MockTransport(handler)).upsert_event(
        "synthetic-access-token",
        "shiftmate0123456789abcdef",
        {
            "summary": "Shift · day",
            "start": {"dateTime": "2026-09-02T01:00:00+00:00"},
            "end": {"dateTime": "2026-09-02T09:00:00+00:00"},
        },
    )

    assert [request.method for request in requests] == ["POST", "PUT"]
    assert requests[1].url.path.endswith("/shiftmate0123456789abcdef")
    assert json.loads(requests[0].content)["id"] == "shiftmate0123456789abcdef"
    assert "id" not in json.loads(requests[1].content)
