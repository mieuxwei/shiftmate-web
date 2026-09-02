from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx


class GoogleCalendarError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class GoogleTokenRevokedError(GoogleCalendarError):
    pass


@dataclass(frozen=True, slots=True)
class GoogleToken:
    access_token: str
    refresh_token: str | None
    expires_in: int | None
    scopes: tuple[str, ...]


class GoogleCalendarClient:
    token_url = "https://oauth2.googleapis.com/token"
    api_root = "https://www.googleapis.com/calendar/v3"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.timeout = timeout
        self.transport = transport

    async def exchange_code(self, code: str, verifier: str) -> GoogleToken:
        return await self._token_request(
            {
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            }
        )

    async def refresh(self, refresh_token: str) -> GoogleToken:
        return await self._token_request(
            {
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
            },
            revoked_on_invalid_grant=True,
        )

    async def upsert_event(
        self, access_token: str, event_id: str, event: dict[str, Any]
    ) -> None:
        headers = {"Authorization": f"Bearer {access_token}"}
        body = {**event, "id": event_id}
        async with httpx.AsyncClient(
            timeout=self.timeout, transport=self.transport
        ) as client:
            try:
                response = await client.post(
                    f"{self.api_root}/calendars/primary/events",
                    headers=headers,
                    json=body,
                )
                if response.status_code == 409:
                    response = await client.put(
                        f"{self.api_root}/calendars/primary/events/"
                        f"{quote(event_id, safe='')}",
                        headers=headers,
                        json=event,
                    )
            except httpx.HTTPError as error:
                raise GoogleCalendarError("CALENDAR_UNAVAILABLE") from error
        self._raise_for_api_error(response.status_code)

    async def delete_event(self, access_token: str, event_id: str) -> None:
        async with httpx.AsyncClient(
            timeout=self.timeout, transport=self.transport
        ) as client:
            try:
                response = await client.delete(
                    f"{self.api_root}/calendars/primary/events/"
                    f"{quote(event_id, safe='')}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            except httpx.HTTPError as error:
                raise GoogleCalendarError("CALENDAR_UNAVAILABLE") from error
        if response.status_code == 404:
            return
        self._raise_for_api_error(response.status_code)

    async def _token_request(
        self, payload: dict[str, str], revoked_on_invalid_grant: bool = False
    ) -> GoogleToken:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, transport=self.transport
            ) as client:
                response = await client.post(self.token_url, data=payload)
        except httpx.HTTPError as error:
            raise GoogleCalendarError("CALENDAR_UNAVAILABLE") from error
        data = _safe_json(response)
        if response.status_code >= 400:
            if revoked_on_invalid_grant and data.get("error") == "invalid_grant":
                raise GoogleTokenRevokedError("CALENDAR_AUTH_REVOKED")
            raise GoogleCalendarError("CALENDAR_AUTH_FAILED")
        access_token = data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise GoogleCalendarError("CALENDAR_AUTH_INVALID_RESPONSE")
        scope = data.get("scope", "")
        scopes = tuple(scope.split()) if isinstance(scope, str) else ()
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in")
        return GoogleToken(
            access_token=access_token,
            refresh_token=refresh_token if isinstance(refresh_token, str) else None,
            expires_in=expires_in if isinstance(expires_in, int) else None,
            scopes=scopes,
        )

    @staticmethod
    def _raise_for_api_error(status_code: int) -> None:
        if status_code < 400:
            return
        if status_code in {401, 403}:
            raise GoogleTokenRevokedError("CALENDAR_AUTH_REVOKED")
        if status_code == 429 or status_code >= 500:
            raise GoogleCalendarError("CALENDAR_UNAVAILABLE")
        raise GoogleCalendarError("CALENDAR_SYNC_FAILED")


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        value = response.json()
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}
