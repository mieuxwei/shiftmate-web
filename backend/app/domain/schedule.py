from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ScheduleValidationError(ValueError):
    """Raised when schedule inputs cannot produce a valid calculation."""


class PayRateNotFoundError(ScheduleValidationError):
    """Raised when no pay rate covers a shift's local work date."""


class OverlappingPayRatesError(ScheduleValidationError):
    """Raised when more than one pay rate covers the same work date."""


@dataclass(frozen=True, slots=True)
class Shift:
    start_at: datetime
    end_at: datetime
    break_minutes: int
    timezone: str
    shift_type: str = "day"

    def __post_init__(self) -> None:
        if not _is_aware(self.start_at) or not _is_aware(self.end_at):
            raise ScheduleValidationError("Shift timestamps must be timezone-aware")
        if not self.shift_type.strip():
            raise ScheduleValidationError("Shift type cannot be empty")
        if (
            isinstance(self.break_minutes, bool)
            or not isinstance(self.break_minutes, int)
            or self.break_minutes < 0
            or self.break_minutes > 1440
        ):
            raise ScheduleValidationError(
                "Break minutes must be an integer between 0 and 1440"
            )

        timezone = _load_timezone(self.timezone)
        start_utc = self.start_at.astimezone(UTC)
        end_utc = self.end_at.astimezone(UTC)
        if end_utc <= start_utc:
            raise ScheduleValidationError("Shift end must be after shift start")

        elapsed = end_utc - start_utc
        if timedelta(minutes=self.break_minutes) > elapsed:
            raise ScheduleValidationError("Break cannot exceed shift duration")

        # Resolve the zone during validation so later properties cannot fail.
        self.start_at.astimezone(timezone)

    @property
    def work_date(self) -> date:
        return self.start_at.astimezone(_load_timezone(self.timezone)).date()

    @property
    def elapsed_duration(self) -> timedelta:
        return self.end_at.astimezone(UTC) - self.start_at.astimezone(UTC)

    @property
    def paid_duration(self) -> timedelta:
        return self.elapsed_duration - timedelta(minutes=self.break_minutes)


@dataclass(frozen=True, slots=True)
class PayRate:
    hourly_rate: Decimal
    effective_from: date
    effective_to: date | None = None

    def __post_init__(self) -> None:
        if not self.hourly_rate.is_finite() or self.hourly_rate <= 0:
            raise ScheduleValidationError("Hourly rate must be finite and positive")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ScheduleValidationError(
                "Pay rate end date cannot be before its start date"
            )

    def applies_on(self, work_date: date) -> bool:
        return self.effective_from <= work_date and (
            self.effective_to is None or work_date <= self.effective_to
        )


@dataclass(frozen=True, slots=True)
class ShiftCalculation:
    work_date: date
    elapsed_duration: timedelta
    paid_duration: timedelta
    hourly_rate: Decimal
    estimated_pay: Decimal

    @property
    def paid_hours(self) -> Decimal:
        return duration_hours(self.paid_duration)


def calculate_shift(shift: Shift, pay_rates: Sequence[PayRate]) -> ShiftCalculation:
    """Calculate one shift using the rate effective on its local start date."""
    matching_rates = [rate for rate in pay_rates if rate.applies_on(shift.work_date)]
    if not matching_rates:
        raise PayRateNotFoundError(
            f"No pay rate covers work date {shift.work_date.isoformat()}"
        )
    if len(matching_rates) > 1:
        raise OverlappingPayRatesError(
            f"Multiple pay rates cover work date {shift.work_date.isoformat()}"
        )

    rate = matching_rates[0]
    paid_hours = duration_hours(shift.paid_duration)
    estimated_pay = (paid_hours * rate.hourly_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return ShiftCalculation(
        work_date=shift.work_date,
        elapsed_duration=shift.elapsed_duration,
        paid_duration=shift.paid_duration,
        hourly_rate=rate.hourly_rate,
        estimated_pay=estimated_pay,
    )


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _load_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ScheduleValidationError(f"Unknown timezone: {name}") from error


def duration_hours(duration: timedelta) -> Decimal:
    whole_seconds = duration.days * 86400 + duration.seconds
    exact_seconds = Decimal(whole_seconds) + Decimal(duration.microseconds) / Decimal(
        1_000_000
    )
    return exact_seconds / Decimal(3600)
