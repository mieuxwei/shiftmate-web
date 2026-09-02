from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from backend.app.domain.analytics import calculate_schedule_summary
from backend.app.domain.schedule import PayRate, Shift


def make_shift(
    work_date: date,
    *,
    hours: int,
    break_minutes: int = 0,
    shift_type: str = "day",
) -> Shift:
    start_at = datetime.combine(work_date, datetime.min.time(), tzinfo=UTC)
    return Shift(
        start_at=start_at,
        end_at=start_at + timedelta(hours=hours),
        break_minutes=break_minutes,
        timezone="UTC",
        shift_type=shift_type,
    )


def test_summary_aggregates_hours_pay_types_and_consecutive_days() -> None:
    shifts = [
        make_shift(date(2026, 9, 5), hours=1),
        make_shift(date(2026, 9, 2), hours=8, break_minutes=30, shift_type="night"),
        make_shift(date(2026, 9, 1), hours=8, break_minutes=60),
        make_shift(date(2026, 9, 3), hours=4, shift_type="night"),
        make_shift(date(2026, 9, 2), hours=2),
    ]
    rates = [
        PayRate(Decimal("100.00"), date(2026, 1, 1), date(2026, 9, 3)),
        PayRate(Decimal("120.00"), date(2026, 9, 4)),
    ]

    summary = calculate_schedule_summary(shifts, rates)

    assert summary.shift_count == 5
    assert summary.total_paid_duration == timedelta(hours=21, minutes=30)
    assert summary.total_paid_hours == Decimal("21.5")
    assert summary.estimated_pay == Decimal("2170.00")
    assert summary.shift_type_counts == {"day": 3, "night": 2}
    assert summary.weekly_paid_hours == {date(2026, 8, 31): Decimal("21.5")}
    assert summary.longest_consecutive_days == 3


def test_multiple_shifts_on_one_date_count_as_one_consecutive_day() -> None:
    shifts = [
        make_shift(date(2026, 9, 1), hours=1),
        make_shift(date(2026, 9, 1), hours=2, shift_type="night"),
        make_shift(date(2026, 9, 2), hours=1),
    ]

    summary = calculate_schedule_summary(
        shifts, [PayRate(Decimal("100.00"), date(2026, 1, 1))]
    )

    assert summary.longest_consecutive_days == 2


def test_empty_schedule_has_zero_summary_without_requiring_a_pay_rate() -> None:
    summary = calculate_schedule_summary([], [])

    assert summary.shift_count == 0
    assert summary.total_paid_duration == timedelta()
    assert summary.total_paid_hours == Decimal("0")
    assert summary.estimated_pay == Decimal("0.00")
    assert summary.shift_type_counts == {}
    assert summary.weekly_paid_hours == {}
    assert summary.longest_consecutive_days == 0
