from typing import Literal

from pydantic import BaseModel


class CalendarConnectResponse(BaseModel):
    authorization_url: str


class CalendarStatusResponse(BaseModel):
    configured: bool
    connection_status: Literal["disconnected", "active", "revoked", "error"]
    scopes: list[str]
    ics_available: Literal[True] = True


class CalendarSyncResponse(BaseModel):
    synced: int
    deleted: int
    failed: int
