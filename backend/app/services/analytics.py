from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import Connection

from backend.app.domain.analytics import calculate_schedule_summary
from backend.app.domain.schedule import PayRate, ScheduleValidationError, Shift
from backend.app.repositories.pay_rates import PayRateRepository
from backend.app.repositories.profiles import ProfileRepository
from backend.app.repositories.shifts import ShiftRepository
from backend.app.services.shifts import ProfileNotFoundError


class AnalyticsServiceError(ValueError):
    """Raised when an analytics request is invalid."""


class AnalyticsCalculationError(AnalyticsServiceError):
    """Raised when stored schedule data cannot produce a summary."""


@dataclass(frozen=True, slots=True)
class AnalyticsSummary:
    date_from: date
    date_to: date
    timezone: str
    currency: str
    shift_count: int
    total_paid_hours: Decimal
    estimated_pay: Decimal
    shift_type_counts: dict[str, int]
    weekly_hours: dict[date, Decimal]
    longest_consecutive_days: int


class AnalyticsService:
    def __init__(
        self,
        profile_repository: ProfileRepository,
        shift_repository: ShiftRepository,
        pay_rate_repository: PayRateRepository,
    ) -> None:
        self.profile_repository = profile_repository
        self.shift_repository = shift_repository
        self.pay_rate_repository = pay_rate_repository

    def get_summary(
        self, connection: Connection, date_from: date, date_to: date
    ) -> AnalyticsSummary:
        if date_to < date_from:
            raise AnalyticsServiceError("date_to cannot be before date_from")
        if date_to - date_from > timedelta(days=365):
            raise AnalyticsServiceError("Analytics date range cannot exceed 366 days")

        profile = self.profile_repository.get_preferences(connection)
        if profile is None:
            raise ProfileNotFoundError("Authenticated user profile was not found")

        shift_records = self.shift_repository.list_shifts(
            connection, date_from, date_to
        )
        pay_rate_records = self.pay_rate_repository.list_pay_rates(connection)
        try:
            shifts = [
                Shift(
                    start_at=record.start_at,
                    end_at=record.end_at,
                    break_minutes=record.break_minutes,
                    timezone=profile.timezone,
                    shift_type=record.shift_type,
                )
                for record in shift_records
            ]
            for record, shift in zip(shift_records, shifts, strict=True):
                if record.work_date != shift.work_date:
                    raise ScheduleValidationError(
                        f"Stored work date does not match shift {record.id}"
                    )
            pay_rates = [
                PayRate(
                    hourly_rate=record.hourly_rate,
                    effective_from=record.effective_from,
                    effective_to=record.effective_to,
                )
                for record in pay_rate_records
            ]
            summary = calculate_schedule_summary(shifts, pay_rates)
        except ScheduleValidationError as error:
            raise AnalyticsCalculationError(str(error)) from error

        return AnalyticsSummary(
            date_from=date_from,
            date_to=date_to,
            timezone=profile.timezone,
            currency=profile.currency,
            shift_count=summary.shift_count,
            total_paid_hours=summary.total_paid_hours,
            estimated_pay=summary.estimated_pay,
            shift_type_counts=summary.shift_type_counts,
            weekly_hours=summary.weekly_paid_hours,
            longest_consecutive_days=summary.longest_consecutive_days,
        )
