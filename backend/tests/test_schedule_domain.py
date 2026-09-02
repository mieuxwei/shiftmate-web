from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from backend.app.domain.schedule import (
    OverlappingPayRatesError,
    PayRate,
    PayRateNotFoundError,
    ScheduleValidationError,
    Shift,
    calculate_shift,
)


def test_cross_midnight_shift_subtracts_break_and_uses_local_start_date() -> None:
    taipei = ZoneInfo("Asia/Taipei")
    shift = Shift(
        start_at=datetime(2026, 9, 2, 22, 0, tzinfo=taipei),
        end_at=datetime(2026, 9, 3, 6, 0, tzinfo=taipei),
        break_minutes=30,
        timezone="Asia/Taipei",
    )

    result = calculate_shift(
        shift,
        [PayRate(Decimal("200.00"), effective_from=date(2026, 9, 1))],
    )

    assert result.work_date == date(2026, 9, 2)
    assert result.elapsed_duration == timedelta(hours=8)
    assert result.paid_duration == timedelta(hours=7, minutes=30)
    assert result.paid_hours == Decimal("7.5")
    assert result.estimated_pay == Decimal("1500.00")


@pytest.mark.parametrize(
    ("start_at", "end_at", "expected"),
    [
        (
            datetime(2026, 3, 8, 1, 30, tzinfo=ZoneInfo("America/New_York")),
            datetime(2026, 3, 8, 3, 30, tzinfo=ZoneInfo("America/New_York")),
            timedelta(hours=1),
        ),
        (
            datetime(2026, 11, 1, 0, 30, tzinfo=ZoneInfo("America/New_York")),
            datetime(2026, 11, 1, 2, 30, tzinfo=ZoneInfo("America/New_York")),
            timedelta(hours=3),
        ),
    ],
)
def test_duration_uses_elapsed_instants_across_daylight_saving_changes(
    start_at: datetime, end_at: datetime, expected: timedelta
) -> None:
    shift = Shift(start_at, end_at, break_minutes=0, timezone="America/New_York")

    assert shift.elapsed_duration == expected


def test_timestamp_offsets_are_converted_to_the_profile_timezone() -> None:
    shift = Shift(
        start_at=datetime(2026, 9, 2, 16, 30, tzinfo=UTC),
        end_at=datetime(2026, 9, 2, 18, 30, tzinfo=UTC),
        break_minutes=0,
        timezone="Asia/Taipei",
    )

    assert shift.work_date == date(2026, 9, 3)


def test_pay_rate_periods_are_inclusive_and_selected_by_work_date() -> None:
    shift = Shift(
        start_at=datetime(2026, 9, 2, 23, 0, tzinfo=UTC),
        end_at=datetime(2026, 9, 3, 1, 0, tzinfo=UTC),
        break_minutes=0,
        timezone="UTC",
    )
    rates = [
        PayRate(
            Decimal("100.00"),
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 9, 2),
        ),
        PayRate(Decimal("120.00"), effective_from=date(2026, 9, 3)),
    ]

    result = calculate_shift(shift, rates)

    assert result.hourly_rate == Decimal("100.00")
    assert result.estimated_pay == Decimal("200.00")


def test_pay_is_rounded_to_cents_with_half_up_rounding() -> None:
    shift = Shift(
        start_at=datetime(2026, 9, 2, 9, 0, tzinfo=UTC),
        end_at=datetime(2026, 9, 2, 9, 1, tzinfo=UTC),
        break_minutes=0,
        timezone="UTC",
    )

    result = calculate_shift(
        shift,
        [PayRate(Decimal("100.50"), effective_from=date(2026, 1, 1))],
    )

    assert result.estimated_pay == Decimal("1.68")


def test_missing_or_overlapping_pay_rates_are_rejected() -> None:
    shift = Shift(
        start_at=datetime(2026, 9, 2, 9, 0, tzinfo=UTC),
        end_at=datetime(2026, 9, 2, 10, 0, tzinfo=UTC),
        break_minutes=0,
        timezone="UTC",
    )

    with pytest.raises(PayRateNotFoundError):
        calculate_shift(shift, [])

    with pytest.raises(OverlappingPayRatesError):
        calculate_shift(
            shift,
            [
                PayRate(Decimal("100"), date(2026, 1, 1)),
                PayRate(Decimal("120"), date(2026, 9, 1)),
            ],
        )


def test_invalid_shift_inputs_are_rejected() -> None:
    with pytest.raises(ScheduleValidationError, match="timezone-aware"):
        Shift(datetime(2026, 9, 2, 9), datetime(2026, 9, 2, 10), 0, "UTC")
    with pytest.raises(ScheduleValidationError, match="after shift start"):
        Shift(
            datetime(2026, 9, 2, 10, tzinfo=UTC),
            datetime(2026, 9, 2, 9, tzinfo=UTC),
            0,
            "UTC",
        )
    with pytest.raises(ScheduleValidationError, match="Break cannot exceed"):
        Shift(
            datetime(2026, 9, 2, 9, tzinfo=UTC),
            datetime(2026, 9, 2, 10, tzinfo=UTC),
            61,
            "UTC",
        )
    with pytest.raises(ScheduleValidationError, match="between 0 and 1440"):
        Shift(
            datetime(2026, 9, 1, 9, tzinfo=UTC),
            datetime(2026, 9, 3, 10, tzinfo=UTC),
            1441,
            "UTC",
        )
    with pytest.raises(ScheduleValidationError, match="Unknown timezone"):
        Shift(
            datetime(2026, 9, 2, 9, tzinfo=UTC),
            datetime(2026, 9, 2, 10, tzinfo=UTC),
            0,
            "Mars/Olympus_Mons",
        )
    with pytest.raises(ScheduleValidationError, match="Shift type cannot be empty"):
        Shift(
            datetime(2026, 9, 2, 9, tzinfo=UTC),
            datetime(2026, 9, 2, 10, tzinfo=UTC),
            0,
            "UTC",
            "  ",
        )


def test_invalid_pay_rate_is_rejected() -> None:
    with pytest.raises(ScheduleValidationError, match="finite and positive"):
        PayRate(Decimal("0"), date(2026, 1, 1))
    with pytest.raises(ScheduleValidationError, match="before its start"):
        PayRate(Decimal("100"), date(2026, 2, 1), date(2026, 1, 31))
