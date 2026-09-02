from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from backend.app.domain.schedule import (
    PayRate,
    Shift,
    calculate_shift,
    duration_hours,
)


@dataclass(frozen=True, slots=True)
class ScheduleSummary:
    shift_count: int
    total_paid_duration: timedelta
    estimated_pay: Decimal
    shift_type_counts: dict[str, int]
    weekly_paid_durations: dict[date, timedelta]
    longest_consecutive_days: int

    @property
    def total_paid_hours(self) -> Decimal:
        return duration_hours(self.total_paid_duration)

    @property
    def weekly_paid_hours(self) -> dict[date, Decimal]:
        return {
            week_start: duration_hours(duration)
            for week_start, duration in self.weekly_paid_durations.items()
        }


def calculate_schedule_summary(
    shifts: Sequence[Shift], pay_rates: Sequence[PayRate]
) -> ScheduleSummary:
    """Aggregate deterministic facts for a dashboard date range."""
    total_paid_duration = timedelta()
    estimated_pay = Decimal("0.00")
    shift_type_counts: dict[str, int] = {}
    weekly_paid_durations: dict[date, timedelta] = {}
    work_dates: set[date] = set()

    for shift in shifts:
        calculation = calculate_shift(shift, pay_rates)
        total_paid_duration += calculation.paid_duration
        estimated_pay += calculation.estimated_pay
        shift_type_counts[shift.shift_type] = (
            shift_type_counts.get(shift.shift_type, 0) + 1
        )
        work_date = calculation.work_date
        work_dates.add(work_date)
        week_start = work_date - timedelta(days=work_date.weekday())
        weekly_paid_durations[week_start] = (
            weekly_paid_durations.get(week_start, timedelta())
            + calculation.paid_duration
        )

    return ScheduleSummary(
        shift_count=len(shifts),
        total_paid_duration=total_paid_duration,
        estimated_pay=estimated_pay,
        shift_type_counts=dict(sorted(shift_type_counts.items())),
        weekly_paid_durations=dict(sorted(weekly_paid_durations.items())),
        longest_consecutive_days=_longest_consecutive_run(work_dates),
    )


def _longest_consecutive_run(work_dates: set[date]) -> int:
    longest = 0
    current = 0
    previous: date | None = None

    for work_date in sorted(work_dates):
        current = (
            current + 1 if previous and work_date - previous == timedelta(1) else 1
        )
        longest = max(longest, current)
        previous = work_date

    return longest
