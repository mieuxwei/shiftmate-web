from collections.abc import Callable
from datetime import date
from typing import Protocol, TypeVar

import anyio
from langchain_core.embeddings import Embeddings
from sqlalchemy import Connection, Engine

from backend.app.core.auth import AuthenticatedUser
from backend.app.core.database import (
    authenticated_connection,
    build_engine,
    build_quota_engine,
)
from backend.app.core.quotas import RequestQuotaGuard
from backend.app.core.settings import Settings
from backend.app.integrations.gemini_assistant import GeminiAssistantAdapter
from backend.app.integrations.gemini_rag import GeminiEmbeddings, GeminiRagError
from backend.app.mcp.schemas import (
    CalendarExportResult,
    ComplianceAnalysisResult,
    PayrollSummaryResult,
    PolicySearchResult,
    ShiftListResult,
    WorkHoursResult,
)
from backend.app.repositories.pay_rates import PostgresPayRateRepository
from backend.app.repositories.policies import PostgresPolicyRepository
from backend.app.repositories.profiles import PostgresProfileRepository
from backend.app.repositories.shifts import PostgresShiftRepository
from backend.app.schemas.shifts import ShiftResponse
from backend.app.services.analytics import AnalyticsService, AnalyticsSummary
from backend.app.services.assistant_factory import build_assistant_service
from backend.app.services.calendar_exports import CalendarExportService
from backend.app.services.policies import PolicyService
from backend.app.services.shifts import ShiftService

T = TypeVar("T")
PAYROLL_DISCLAIMER = "Estimated pay only; not legal, HR, or payroll advice."


class McpOperationError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class McpOperations(Protocol):
    async def get_shifts(
        self,
        user: AuthenticatedUser,
        date_from: date | None,
        date_to: date | None,
    ) -> ShiftListResult: ...

    async def calculate_work_hours(
        self, user: AuthenticatedUser, date_from: date, date_to: date
    ) -> WorkHoursResult: ...

    async def get_payroll_summary(
        self, user: AuthenticatedUser, date_from: date, date_to: date
    ) -> PayrollSummaryResult: ...

    async def search_work_policy(
        self, user: AuthenticatedUser, question: str
    ) -> PolicySearchResult: ...

    async def analyze_schedule_compliance(
        self,
        user: AuthenticatedUser,
        question: str,
        date_from: date,
        date_to: date,
    ) -> ComplianceAnalysisResult: ...

    async def create_calendar_export(
        self,
        user: AuthenticatedUser,
        date_from: date | None,
        date_to: date | None,
    ) -> CalendarExportResult: ...


class DatabaseMcpOperations:
    """Stateless MCP adapters over owner-scoped application services."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.shift_repository = PostgresShiftRepository()
        self.shift_service = ShiftService(self.shift_repository)
        self.analytics_service = AnalyticsService(
            PostgresProfileRepository(),
            self.shift_repository,
            PostgresPayRateRepository(),
        )
        self.policy_service = PolicyService(PostgresPolicyRepository())
        self.calendar_export_service = CalendarExportService(self.shift_repository)

    async def get_shifts(
        self,
        user: AuthenticatedUser,
        date_from: date | None,
        date_to: date | None,
    ) -> ShiftListResult:
        _validate_date_range(date_from, date_to)

        def operation(connection: Connection) -> ShiftListResult:
            records = self.shift_service.list_shifts(connection, date_from, date_to)
            return ShiftListResult(
                shifts=[ShiftResponse.model_validate(item) for item in records]
            )

        return await self._run(user, operation)

    async def calculate_work_hours(
        self, user: AuthenticatedUser, date_from: date, date_to: date
    ) -> WorkHoursResult:
        def operation(connection: Connection) -> WorkHoursResult:
            summary = self.analytics_service.get_summary(connection, date_from, date_to)
            return _hours_result(summary)

        return await self._run(user, operation)

    async def get_payroll_summary(
        self, user: AuthenticatedUser, date_from: date, date_to: date
    ) -> PayrollSummaryResult:
        def operation(connection: Connection) -> PayrollSummaryResult:
            summary = self.analytics_service.get_summary(connection, date_from, date_to)
            return PayrollSummaryResult(
                date_from=summary.date_from,
                date_to=summary.date_to,
                currency=summary.currency,
                shift_count=summary.shift_count,
                total_paid_hours=summary.total_paid_hours,
                estimated_pay=summary.estimated_pay,
                disclaimer=PAYROLL_DISCLAIMER,
            )

        return await self._run(user, operation)

    async def search_work_policy(
        self, user: AuthenticatedUser, question: str
    ) -> PolicySearchResult:
        def operation(connection: Connection) -> PolicySearchResult:
            embeddings = self._required_embeddings(user)
            evidence = self.policy_service.retrieve_evidence(
                connection,
                question,
                embeddings,
                self.settings.rag_top_k,
                self.settings.rag_score_threshold,
            )
            return PolicySearchResult(
                question=question,
                refused=not evidence,
                citations=[item.citation for item in evidence],
            )

        return await self._run(user, operation)

    async def analyze_schedule_compliance(
        self,
        user: AuthenticatedUser,
        question: str,
        date_from: date,
        date_to: date,
    ) -> ComplianceAnalysisResult:
        def operation(connection: Connection) -> ComplianceAnalysisResult:
            model = self._assistant_model(user)
            service = build_assistant_service(
                self.analytics_service,
                self.policy_service,
                self._optional_embeddings(user),
                model,
                top_k=self.settings.rag_top_k,
                score_threshold=self.settings.rag_score_threshold,
            )
            return ComplianceAnalysisResult(
                result=service.query(connection, question, date_from, date_to)
            )

        return await self._run(user, operation)

    async def create_calendar_export(
        self,
        user: AuthenticatedUser,
        date_from: date | None,
        date_to: date | None,
    ) -> CalendarExportResult:
        _validate_date_range(date_from, date_to)

        def operation(connection: Connection) -> CalendarExportResult:
            result = self.calendar_export_service.create_export(
                connection, date_from, date_to
            )
            return CalendarExportResult(
                filename=result.filename,
                media_type=result.media_type,
                content=result.content.decode("utf-8"),
            )

        return await self._run(user, operation)

    async def _run(
        self, user: AuthenticatedUser, operation: Callable[[Connection], T]
    ) -> T:
        return await anyio.to_thread.run_sync(self._run_sync, user, operation)

    def _run_sync(
        self, user: AuthenticatedUser, operation: Callable[[Connection], T]
    ) -> T:
        engine = self._engine()
        with authenticated_connection(engine, user) as connection:
            return operation(connection)

    def _engine(self) -> Engine:
        if self.settings.database_url is None:
            raise McpOperationError("MCP_DATABASE_NOT_CONFIGURED")
        if self.settings.database_request_role != "authenticated":
            raise McpOperationError("MCP_DATABASE_ROLE_INVALID")
        return build_engine(
            self.settings.database_url,
            self.settings.database_pool_size,
            self.settings.database_max_overflow,
        )

    def _required_embeddings(self, user: AuthenticatedUser) -> Embeddings:
        if not self.settings.gemini_api_key:
            raise GeminiRagError("GEMINI_NOT_CONFIGURED")
        return GeminiEmbeddings(
            self.settings.gemini_api_key,
            self.settings.gemini_embedding_model,
            self.settings.gemini_timeout_seconds,
            self.settings.gemini_embedding_dimensions,
            self._quota_guard(user).consume_gemini_request,
        )

    def _optional_embeddings(self, user: AuthenticatedUser) -> Embeddings | None:
        if not self.settings.gemini_api_key:
            return None
        return self._required_embeddings(user)

    def _assistant_model(
        self, user: AuthenticatedUser
    ) -> GeminiAssistantAdapter | None:
        if not self.settings.gemini_api_key:
            return None
        return GeminiAssistantAdapter(
            self.settings.gemini_api_key,
            self.settings.gemini_model,
            self.settings.gemini_timeout_seconds,
            self._quota_guard(user).consume_gemini_request,
        )

    def _quota_guard(self, user: AuthenticatedUser) -> RequestQuotaGuard:
        return RequestQuotaGuard(
            build_quota_engine(self.settings.database_url or ""),
            user,
            self.settings.gemini_daily_request_cap,
            self.settings.upload_daily_cap_per_owner,
        )


def _hours_result(summary: AnalyticsSummary) -> WorkHoursResult:
    return WorkHoursResult(
        date_from=summary.date_from,
        date_to=summary.date_to,
        timezone=summary.timezone,
        shift_count=summary.shift_count,
        total_paid_hours=summary.total_paid_hours,
        weekly_hours=summary.weekly_hours,
        longest_consecutive_days=summary.longest_consecutive_days,
    )


def _validate_date_range(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None:
        if date_to < date_from:
            raise McpOperationError("DATE_RANGE_INVALID")
        if (date_to - date_from).days > 365:
            raise McpOperationError("DATE_RANGE_TOO_LARGE")
