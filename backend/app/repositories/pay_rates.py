from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy import Connection, RowMapping, text


@dataclass(frozen=True, slots=True)
class NewPayRate:
    hourly_rate: Decimal
    effective_from: date
    effective_to: date | None


@dataclass(frozen=True, slots=True)
class PayRateRecord:
    id: UUID
    hourly_rate: Decimal
    effective_from: date
    effective_to: date | None
    created_at: datetime
    updated_at: datetime


class PayRateRepository(Protocol):
    def profile_exists(self, connection: Connection) -> bool: ...

    def lock_owner_rates(self, connection: Connection) -> None: ...

    def list_pay_rates(self, connection: Connection) -> Sequence[PayRateRecord]: ...

    def get_pay_rate(
        self, connection: Connection, pay_rate_id: UUID
    ) -> PayRateRecord | None: ...

    def has_overlap(
        self,
        connection: Connection,
        pay_rate: NewPayRate,
        exclude_id: UUID | None = None,
    ) -> bool: ...

    def create_pay_rate(
        self, connection: Connection, pay_rate: NewPayRate
    ) -> PayRateRecord: ...

    def has_shifts_outside_period(
        self,
        connection: Connection,
        current: PayRateRecord,
        replacement: NewPayRate,
    ) -> bool: ...

    def has_shifts(self, connection: Connection, pay_rate: PayRateRecord) -> bool: ...

    def update_pay_rate(
        self, connection: Connection, pay_rate_id: UUID, pay_rate: NewPayRate
    ) -> PayRateRecord | None: ...

    def delete_pay_rate(self, connection: Connection, pay_rate_id: UUID) -> bool: ...


class PostgresPayRateRepository:
    _columns = """
        id, hourly_rate, effective_from, effective_to, created_at, updated_at
    """

    def profile_exists(self, connection: Connection) -> bool:
        return (
            connection.execute(text("SELECT 1 FROM profiles")).scalar_one_or_none()
            is not None
        )

    def lock_owner_rates(self, connection: Connection) -> None:
        connection.execute(
            text(
                """
                SELECT pg_advisory_xact_lock(
                    hashtextextended(app_private.current_user_id()::text, 0)
                )
                """
            )
        )

    def list_pay_rates(self, connection: Connection) -> Sequence[PayRateRecord]:
        rows = connection.execute(
            text(
                f"""
                SELECT {self._columns}
                FROM pay_rates
                ORDER BY effective_from, id
                """
            )
        )
        return [_to_record(row._mapping) for row in rows]

    def get_pay_rate(
        self, connection: Connection, pay_rate_id: UUID
    ) -> PayRateRecord | None:
        row = connection.execute(
            text(
                f"""
                SELECT {self._columns}
                FROM pay_rates
                WHERE id = :pay_rate_id
                """
            ),
            {"pay_rate_id": pay_rate_id},
        ).one_or_none()
        return _to_record(row._mapping) if row is not None else None

    def has_overlap(
        self,
        connection: Connection,
        pay_rate: NewPayRate,
        exclude_id: UUID | None = None,
    ) -> bool:
        exclusion = "AND id <> :exclude_id" if exclude_id is not None else ""
        return (
            connection.execute(
                text(
                    f"""
                    SELECT 1
                    FROM pay_rates
                    WHERE effective_from <= COALESCE(
                              CAST(:effective_to AS date), 'infinity'::date
                          )
                      AND COALESCE(effective_to, 'infinity'::date)
                          >= :effective_from
                      {exclusion}
                    LIMIT 1
                    """
                ),
                {
                    "effective_from": pay_rate.effective_from,
                    "effective_to": pay_rate.effective_to,
                    **({"exclude_id": exclude_id} if exclude_id is not None else {}),
                },
            ).scalar_one_or_none()
            is not None
        )

    def create_pay_rate(
        self, connection: Connection, pay_rate: NewPayRate
    ) -> PayRateRecord:
        row = connection.execute(
            text(
                f"""
                INSERT INTO pay_rates (
                    owner_id, hourly_rate, effective_from, effective_to
                )
                VALUES (
                    app_private.current_user_id(), :hourly_rate,
                    :effective_from, :effective_to
                )
                RETURNING {self._columns}
                """
            ),
            {
                "hourly_rate": pay_rate.hourly_rate,
                "effective_from": pay_rate.effective_from,
                "effective_to": pay_rate.effective_to,
            },
        ).one()
        return _to_record(row._mapping)

    def has_shifts_outside_period(
        self,
        connection: Connection,
        current: PayRateRecord,
        replacement: NewPayRate,
    ) -> bool:
        current_end = (
            "AND work_date <= :current_to" if current.effective_to is not None else ""
        )
        after_replacement = (
            "OR work_date > :replacement_to"
            if replacement.effective_to is not None
            else ""
        )
        parameters: dict[str, date] = {
            "current_from": current.effective_from,
            "replacement_from": replacement.effective_from,
        }
        if current.effective_to is not None:
            parameters["current_to"] = current.effective_to
        if replacement.effective_to is not None:
            parameters["replacement_to"] = replacement.effective_to
        return (
            connection.execute(
                text(
                    f"""
                    SELECT 1
                    FROM shifts
                    WHERE work_date >= :current_from
                      {current_end}
                      AND (
                          work_date < :replacement_from
                          {after_replacement}
                      )
                    LIMIT 1
                    """
                ),
                parameters,
            ).scalar_one_or_none()
            is not None
        )

    def has_shifts(self, connection: Connection, pay_rate: PayRateRecord) -> bool:
        end_clause = (
            "AND work_date <= :effective_to"
            if pay_rate.effective_to is not None
            else ""
        )
        parameters = {"effective_from": pay_rate.effective_from}
        if pay_rate.effective_to is not None:
            parameters["effective_to"] = pay_rate.effective_to
        return (
            connection.execute(
                text(
                    f"""
                    SELECT 1
                    FROM shifts
                    WHERE work_date >= :effective_from
                      {end_clause}
                    LIMIT 1
                    """
                ),
                parameters,
            ).scalar_one_or_none()
            is not None
        )

    def update_pay_rate(
        self, connection: Connection, pay_rate_id: UUID, pay_rate: NewPayRate
    ) -> PayRateRecord | None:
        row = connection.execute(
            text(
                f"""
                UPDATE pay_rates
                SET hourly_rate = :hourly_rate,
                    effective_from = :effective_from,
                    effective_to = :effective_to,
                    updated_at = now()
                WHERE id = :pay_rate_id
                RETURNING {self._columns}
                """
            ),
            {
                "pay_rate_id": pay_rate_id,
                "hourly_rate": pay_rate.hourly_rate,
                "effective_from": pay_rate.effective_from,
                "effective_to": pay_rate.effective_to,
            },
        ).one_or_none()
        return _to_record(row._mapping) if row is not None else None

    def delete_pay_rate(self, connection: Connection, pay_rate_id: UUID) -> bool:
        deleted_id = connection.execute(
            text("DELETE FROM pay_rates WHERE id = :pay_rate_id RETURNING id"),
            {"pay_rate_id": pay_rate_id},
        ).scalar_one_or_none()
        return deleted_id is not None


def _to_record(row: RowMapping) -> PayRateRecord:
    return PayRateRecord(
        id=row["id"],
        hourly_rate=row["hourly_rate"],
        effective_from=row["effective_from"],
        effective_to=row["effective_to"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
