from typing import Protocol
from uuid import UUID

from sqlalchemy import Connection, text


class ShiftRepository(Protocol):
    def list_ids(self, connection: Connection) -> list[UUID]: ...


class PostgresShiftRepository:
    def list_ids(self, connection: Connection) -> list[UUID]:
        rows = connection.execute(text("SELECT id FROM shifts ORDER BY id"))
        return [row.id for row in rows]
