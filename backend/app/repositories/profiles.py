from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import Connection, text


@dataclass(frozen=True, slots=True)
class ProfilePreferences:
    timezone: str
    currency: str


class ProfileRepository(Protocol):
    def get_preferences(self, connection: Connection) -> ProfilePreferences | None: ...


class PostgresProfileRepository:
    def get_preferences(self, connection: Connection) -> ProfilePreferences | None:
        row = connection.execute(
            text("SELECT timezone, currency FROM profiles")
        ).one_or_none()
        if row is None:
            return None
        return ProfilePreferences(timezone=row.timezone, currency=row.currency)
