from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy import Connection

from backend.app.repositories.pay_rates import NewPayRate, PayRateRecord
from backend.app.services.pay_rates import (
    CreatePayRateCommand,
    PayRateInUseError,
    PayRateOverlapError,
    PayRateRecordNotFoundError,
    PayRateService,
    PayRateServiceError,
    UpdatePayRateCommand,
)
from backend.app.services.shifts import ProfileNotFoundError


class FakePayRateRepository:
    def __init__(self, *, profile_exists: bool = True) -> None:
        self.has_profile = profile_exists
        self.locked = False
        self.records: list[PayRateRecord] = []
        self.used_dates: set[date] = set()

    def profile_exists(self, connection: Connection) -> bool:
        return self.has_profile

    def lock_owner_rates(self, connection: Connection) -> None:
        self.locked = True

    def list_pay_rates(self, connection: Connection) -> list[PayRateRecord]:
        return self.records

    def get_pay_rate(
        self, connection: Connection, pay_rate_id: UUID
    ) -> PayRateRecord | None:
        return next(
            (record for record in self.records if record.id == pay_rate_id), None
        )

    def has_overlap(
        self,
        connection: Connection,
        pay_rate: NewPayRate,
        exclude_id: UUID | None = None,
    ) -> bool:
        assert self.locked
        new_end = pay_rate.effective_to or date.max
        return any(
            existing.id != exclude_id
            and existing.effective_from <= new_end
            and (existing.effective_to or date.max) >= pay_rate.effective_from
            for existing in self.records
        )

    def create_pay_rate(
        self, connection: Connection, pay_rate: NewPayRate
    ) -> PayRateRecord:
        now = datetime(2026, 9, 2, tzinfo=UTC)
        record = PayRateRecord(
            id=UUID(int=len(self.records) + 1),
            hourly_rate=pay_rate.hourly_rate,
            effective_from=pay_rate.effective_from,
            effective_to=pay_rate.effective_to,
            created_at=now,
            updated_at=now,
        )
        self.records.append(record)
        return record

    def has_shifts_outside_period(
        self,
        connection: Connection,
        current: PayRateRecord,
        replacement: NewPayRate,
    ) -> bool:
        current_end = current.effective_to or date.max
        replacement_end = replacement.effective_to or date.max
        return any(
            current.effective_from <= work_date <= current_end
            and not replacement.effective_from <= work_date <= replacement_end
            for work_date in self.used_dates
        )

    def has_shifts(self, connection: Connection, pay_rate: PayRateRecord) -> bool:
        effective_end = pay_rate.effective_to or date.max
        return any(
            pay_rate.effective_from <= work_date <= effective_end
            for work_date in self.used_dates
        )

    def update_pay_rate(
        self, connection: Connection, pay_rate_id: UUID, pay_rate: NewPayRate
    ) -> PayRateRecord | None:
        current = self.get_pay_rate(connection, pay_rate_id)
        if current is None:
            return None
        updated = PayRateRecord(
            id=pay_rate_id,
            hourly_rate=pay_rate.hourly_rate,
            effective_from=pay_rate.effective_from,
            effective_to=pay_rate.effective_to,
            created_at=current.created_at,
            updated_at=datetime(2026, 9, 3, tzinfo=UTC),
        )
        self.records[self.records.index(current)] = updated
        return updated

    def delete_pay_rate(self, connection: Connection, pay_rate_id: UUID) -> bool:
        current = self.get_pay_rate(connection, pay_rate_id)
        if current is None:
            return False
        self.records.remove(current)
        return True


CONNECTION = cast(Connection, object())


def test_create_locks_owner_and_accepts_adjacent_periods() -> None:
    repository = FakePayRateRepository()
    service = PayRateService(repository)
    first = service.create_pay_rate(
        CONNECTION,
        CreatePayRateCommand(Decimal("200.00"), date(2026, 1, 1), date(2026, 6, 30)),
    )
    second = service.create_pay_rate(
        CONNECTION,
        CreatePayRateCommand(Decimal("220.00"), date(2026, 7, 1), None),
    )

    assert repository.locked is True
    assert service.list_pay_rates(CONNECTION) == [first, second]


def test_create_rejects_overlapping_or_invalid_periods() -> None:
    repository = FakePayRateRepository()
    service = PayRateService(repository)
    service.create_pay_rate(
        CONNECTION,
        CreatePayRateCommand(Decimal("200.00"), date(2026, 1, 1), date(2026, 6, 30)),
    )

    with pytest.raises(PayRateOverlapError):
        service.create_pay_rate(
            CONNECTION,
            CreatePayRateCommand(Decimal("220.00"), date(2026, 6, 30), None),
        )
    with pytest.raises(PayRateServiceError, match="before its start"):
        service.create_pay_rate(
            CONNECTION,
            CreatePayRateCommand(
                Decimal("220.00"), date(2026, 8, 1), date(2026, 7, 31)
            ),
        )


def test_create_requires_an_owner_profile() -> None:
    service = PayRateService(FakePayRateRepository(profile_exists=False))

    with pytest.raises(ProfileNotFoundError):
        service.create_pay_rate(
            CONNECTION,
            CreatePayRateCommand(Decimal("200.00"), date(2026, 1, 1), None),
        )


def test_update_reprices_but_rejects_overlap_or_uncovered_used_dates() -> None:
    repository = FakePayRateRepository()
    service = PayRateService(repository)
    first = service.create_pay_rate(
        CONNECTION,
        CreatePayRateCommand(Decimal("200.00"), date(2026, 1, 1), date(2026, 6, 30)),
    )
    service.create_pay_rate(
        CONNECTION,
        CreatePayRateCommand(Decimal("220.00"), date(2026, 7, 1), None),
    )
    repository.used_dates.add(date(2026, 2, 1))

    updated = service.update_pay_rate(
        CONNECTION, first.id, UpdatePayRateCommand(hourly_rate=Decimal("205.00"))
    )
    assert updated.hourly_rate == Decimal("205.00")

    with pytest.raises(PayRateOverlapError):
        service.update_pay_rate(
            CONNECTION,
            first.id,
            UpdatePayRateCommand(
                effective_to=date(2026, 7, 1), effective_to_supplied=True
            ),
        )
    with pytest.raises(PayRateInUseError):
        service.update_pay_rate(
            CONNECTION,
            first.id,
            UpdatePayRateCommand(effective_from=date(2026, 3, 1)),
        )


def test_delete_rejects_used_rate_and_hides_missing_rate() -> None:
    repository = FakePayRateRepository()
    service = PayRateService(repository)
    rate = service.create_pay_rate(
        CONNECTION,
        CreatePayRateCommand(Decimal("200.00"), date(2026, 1, 1), None),
    )
    repository.used_dates.add(date(2026, 2, 1))

    with pytest.raises(PayRateInUseError):
        service.delete_pay_rate(CONNECTION, rate.id)

    repository.used_dates.clear()
    service.delete_pay_rate(CONNECTION, rate.id)
    with pytest.raises(PayRateRecordNotFoundError):
        service.delete_pay_rate(CONNECTION, rate.id)
    with pytest.raises(PayRateRecordNotFoundError):
        service.update_pay_rate(CONNECTION, rate.id, UpdatePayRateCommand())
