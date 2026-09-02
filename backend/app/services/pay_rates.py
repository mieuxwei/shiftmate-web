from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Connection

from backend.app.domain.schedule import PayRate, ScheduleValidationError
from backend.app.repositories.pay_rates import (
    NewPayRate,
    PayRateRecord,
    PayRateRepository,
)
from backend.app.services.shifts import ProfileNotFoundError


class PayRateServiceError(ValueError):
    """Raised when a pay-rate operation cannot be completed."""


class PayRateOverlapError(PayRateServiceError):
    """Raised when an effective period overlaps an existing rate."""


class PayRateRecordNotFoundError(PayRateServiceError):
    """Raised when a pay rate is missing or hidden by owner isolation."""


class PayRateInUseError(PayRateServiceError):
    """Raised when a change would leave existing shifts without their rate."""


@dataclass(frozen=True, slots=True)
class CreatePayRateCommand:
    hourly_rate: Decimal
    effective_from: date
    effective_to: date | None


@dataclass(frozen=True, slots=True)
class UpdatePayRateCommand:
    hourly_rate: Decimal | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    effective_to_supplied: bool = False


class PayRateService:
    def __init__(self, repository: PayRateRepository) -> None:
        self.repository = repository

    def list_pay_rates(self, connection: Connection) -> list[PayRateRecord]:
        return list(self.repository.list_pay_rates(connection))

    def create_pay_rate(
        self, connection: Connection, command: CreatePayRateCommand
    ) -> PayRateRecord:
        if not self.repository.profile_exists(connection):
            raise ProfileNotFoundError("Authenticated user profile was not found")

        try:
            validated = PayRate(
                hourly_rate=command.hourly_rate,
                effective_from=command.effective_from,
                effective_to=command.effective_to,
            )
        except ScheduleValidationError as error:
            raise PayRateServiceError(str(error)) from error

        new_rate = NewPayRate(
            hourly_rate=validated.hourly_rate,
            effective_from=validated.effective_from,
            effective_to=validated.effective_to,
        )
        self.repository.lock_owner_rates(connection)
        if self.repository.has_overlap(connection, new_rate):
            raise PayRateOverlapError(
                "Pay-rate effective period overlaps an existing rate"
            )
        return self.repository.create_pay_rate(connection, new_rate)

    def update_pay_rate(
        self, connection: Connection, pay_rate_id: UUID, command: UpdatePayRateCommand
    ) -> PayRateRecord:
        self.repository.lock_owner_rates(connection)
        current = self.repository.get_pay_rate(connection, pay_rate_id)
        if current is None:
            raise PayRateRecordNotFoundError("Pay rate was not found")

        try:
            validated = PayRate(
                hourly_rate=command.hourly_rate or current.hourly_rate,
                effective_from=command.effective_from or current.effective_from,
                effective_to=(
                    command.effective_to
                    if command.effective_to_supplied
                    else current.effective_to
                ),
            )
        except ScheduleValidationError as error:
            raise PayRateServiceError(str(error)) from error

        replacement = NewPayRate(
            validated.hourly_rate,
            validated.effective_from,
            validated.effective_to,
        )
        if self.repository.has_overlap(connection, replacement, exclude_id=pay_rate_id):
            raise PayRateOverlapError(
                "Pay-rate effective period overlaps an existing rate"
            )
        if self.repository.has_shifts_outside_period(connection, current, replacement):
            raise PayRateInUseError(
                "Pay-rate period cannot exclude shifts that currently use it"
            )

        updated = self.repository.update_pay_rate(connection, pay_rate_id, replacement)
        if updated is None:
            raise PayRateRecordNotFoundError("Pay rate was not found")
        return updated

    def delete_pay_rate(self, connection: Connection, pay_rate_id: UUID) -> None:
        self.repository.lock_owner_rates(connection)
        current = self.repository.get_pay_rate(connection, pay_rate_id)
        if current is None:
            raise PayRateRecordNotFoundError("Pay rate was not found")
        if self.repository.has_shifts(connection, current):
            raise PayRateInUseError("Pay rate cannot be deleted while shifts use it")
        if not self.repository.delete_pay_rate(connection, pay_rate_id):
            raise PayRateRecordNotFoundError("Pay rate was not found")
