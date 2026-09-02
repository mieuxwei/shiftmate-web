from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy import Connection

from backend.app.repositories.pay_rates import PayRateRecord, PayRateRepository
from backend.app.repositories.profiles import ProfilePreferences
from backend.app.repositories.shifts import ShiftRecord, ShiftRepository
from backend.app.services.analytics import (
    AnalyticsCalculationError,
    AnalyticsService,
    AnalyticsServiceError,
)
from backend.app.services.shifts import ProfileNotFoundError


class FakeProfileRepository:
    def __init__(self, profile: ProfilePreferences | None) -> None:
        self.profile = profile

    def get_preferences(self, connection: Connection) -> ProfilePreferences | None:
        return self.profile


class FakeShiftReader:
    def __init__(self, shifts: list[ShiftRecord]) -> None:
        self.shifts = shifts

    def list_shifts(
        self,
        connection: Connection,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ShiftRecord]:
        return self.shifts


class FakePayRateReader:
    def __init__(self, pay_rates: list[PayRateRecord]) -> None:
        self.pay_rates = pay_rates

    def list_pay_rates(self, connection: Connection) -> list[PayRateRecord]:
        return self.pay_rates


CONNECTION = cast(Connection, object())
NOW = datetime(2026, 9, 1, tzinfo=UTC)
DEFAULT_PROFILE = ProfilePreferences("Asia/Taipei", "TWD")


def shift_record(
    shift_id: int,
    work_date: date,
    start_at: datetime,
    end_at: datetime,
    break_minutes: int,
    shift_type: str,
) -> ShiftRecord:
    return ShiftRecord(
        id=UUID(int=shift_id),
        work_date=work_date,
        start_at=start_at,
        end_at=end_at,
        break_minutes=break_minutes,
        shift_type=shift_type,
        notes=None,
        source="manual",
        created_at=NOW,
        updated_at=NOW,
    )


def rate_record() -> PayRateRecord:
    return PayRateRecord(
        id=UUID(int=101),
        hourly_rate=Decimal("200.00"),
        effective_from=date(2026, 1, 1),
        effective_to=None,
        created_at=NOW,
        updated_at=NOW,
    )


def analytics_service(
    shifts: list[ShiftRecord],
    rates: list[PayRateRecord],
    profile: ProfilePreferences | None = DEFAULT_PROFILE,
) -> AnalyticsService:
    return AnalyticsService(
        FakeProfileRepository(profile),
        cast(ShiftRepository, FakeShiftReader(shifts)),
        cast(PayRateRepository, FakePayRateReader(rates)),
    )


def test_summary_matches_deterministic_domain_calculation() -> None:
    shifts = [
        shift_record(
            1,
            date(2026, 9, 1),
            datetime(2026, 9, 1, 1, tzinfo=UTC),
            datetime(2026, 9, 1, 9, tzinfo=UTC),
            60,
            "day",
        ),
        shift_record(
            2,
            date(2026, 9, 2),
            datetime(2026, 9, 2, 14, tzinfo=UTC),
            datetime(2026, 9, 2, 22, tzinfo=UTC),
            30,
            "night",
        ),
    ]

    summary = analytics_service(shifts, [rate_record()]).get_summary(
        CONNECTION, date(2026, 9, 1), date(2026, 9, 3)
    )

    assert summary.timezone == "Asia/Taipei"
    assert summary.currency == "TWD"
    assert summary.shift_count == 2
    assert summary.total_paid_hours == Decimal("14.5")
    assert summary.estimated_pay == Decimal("2900.00")
    assert summary.shift_type_counts == {"day": 1, "night": 1}
    assert summary.weekly_hours == {date(2026, 8, 31): Decimal("14.5")}
    assert summary.longest_consecutive_days == 2


def test_summary_validates_range_and_profile() -> None:
    service = analytics_service([], [])
    with pytest.raises(AnalyticsServiceError, match="before date_from"):
        service.get_summary(CONNECTION, date(2026, 9, 2), date(2026, 9, 1))
    with pytest.raises(AnalyticsServiceError, match="366 days"):
        service.get_summary(CONNECTION, date(2026, 1, 1), date(2027, 1, 2))
    with pytest.raises(ProfileNotFoundError):
        analytics_service([], [], profile=None).get_summary(
            CONNECTION, date(2026, 9, 1), date(2026, 9, 1)
        )


def test_summary_rejects_missing_rate_or_inconsistent_stored_work_date() -> None:
    shift = shift_record(
        1,
        date(2026, 9, 1),
        datetime(2026, 9, 1, 1, tzinfo=UTC),
        datetime(2026, 9, 1, 2, tzinfo=UTC),
        0,
        "day",
    )
    with pytest.raises(AnalyticsCalculationError, match="No pay rate"):
        analytics_service([shift], []).get_summary(
            CONNECTION, date(2026, 9, 1), date(2026, 9, 1)
        )

    inconsistent = shift_record(
        2,
        date(2026, 9, 2),
        shift.start_at,
        shift.end_at,
        0,
        "day",
    )
    with pytest.raises(AnalyticsCalculationError, match="Stored work date"):
        analytics_service([inconsistent], [rate_record()]).get_summary(
            CONNECTION, date(2026, 9, 1), date(2026, 9, 2)
        )
