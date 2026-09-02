from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import TypeVar, cast
from uuid import UUID

import httpx
import httpx2
import pytest
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server.auth.provider import AccessToken
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy import Connection

from backend.app.core.auth import AuthenticatedUser
from backend.app.core.settings import Settings
from backend.app.mcp.operations import DatabaseMcpOperations
from backend.app.mcp.schemas import (
    CalendarExportResult,
    ComplianceAnalysisResult,
    PayrollSummaryResult,
    PolicySearchResult,
    ShiftListResult,
    WorkHoursResult,
)
from backend.app.mcp.server import build_mcp_server
from backend.app.repositories.pay_rates import PayRateRepository
from backend.app.repositories.profiles import ProfilePreferences, ProfileRepository
from backend.app.repositories.shifts import ShiftRepository
from backend.app.schemas.assistant import AssistantQueryResponse
from backend.app.services.analytics import AnalyticsService
from backend.app.services.shifts import ShiftService

pytestmark = pytest.mark.anyio
USER = AuthenticatedUser(UUID("00000000-0000-0000-0000-000000000801"), "authenticated")
DATE_FROM = date(2026, 9, 1)
DATE_TO = date(2026, 9, 7)
TestResultT = TypeVar("TestResultT")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class StaticPrincipal:
    async def require_user(self) -> AuthenticatedUser:
        return USER


class RejectingPrincipal:
    async def require_user(self) -> AuthenticatedUser:
        from backend.app.mcp.auth import McpAuthenticationError

        raise McpAuthenticationError


class SyntheticTokenVerifier:
    async def verify_token(self, token: str) -> AccessToken | None:
        if token != "synthetic-user-token":
            return None
        return AccessToken(
            token=token,
            client_id="synthetic-client",
            scopes=["shiftmate:read"],
            subject=str(USER.id),
            claims={"iss": "https://synthetic.test/auth/v1"},
        )


class FakeOperations:
    def __init__(self) -> None:
        self.calls: list[tuple[str, UUID]] = []

    def _record(self, name: str, user: AuthenticatedUser) -> None:
        self.calls.append((name, user.id))

    async def get_shifts(
        self,
        user: AuthenticatedUser,
        date_from: date | None,
        date_to: date | None,
    ) -> ShiftListResult:
        self._record("get_shifts", user)
        return ShiftListResult(shifts=[])

    async def calculate_work_hours(
        self, user: AuthenticatedUser, date_from: date, date_to: date
    ) -> WorkHoursResult:
        self._record("calculate_work_hours", user)
        return WorkHoursResult(
            date_from=date_from,
            date_to=date_to,
            timezone="Asia/Taipei",
            shift_count=2,
            total_paid_hours=Decimal("14.5"),
            weekly_hours={date(2026, 8, 31): Decimal("14.5")},
            longest_consecutive_days=2,
        )

    async def get_payroll_summary(
        self, user: AuthenticatedUser, date_from: date, date_to: date
    ) -> PayrollSummaryResult:
        self._record("get_payroll_summary", user)
        return PayrollSummaryResult(
            date_from=date_from,
            date_to=date_to,
            currency="TWD",
            shift_count=2,
            total_paid_hours=Decimal("14.5"),
            estimated_pay=Decimal("2900.00"),
            disclaimer="Estimated pay only; not legal, HR, or payroll advice.",
        )

    async def search_work_policy(
        self, user: AuthenticatedUser, question: str
    ) -> PolicySearchResult:
        self._record("search_work_policy", user)
        return PolicySearchResult(question=question, refused=True, citations=[])

    async def analyze_schedule_compliance(
        self,
        user: AuthenticatedUser,
        question: str,
        date_from: date,
        date_to: date,
    ) -> ComplianceAnalysisResult:
        self._record("analyze_schedule_compliance", user)
        return ComplianceAnalysisResult(
            result=AssistantQueryResponse(
                answer="資料不足，無法判定是否符合規章。",
                intent="hybrid",
                refused=True,
                citations=[],
                schedule_facts=None,
                tools=[],
                prompt_version=None,
                model_name=None,
            )
        )

    async def create_calendar_export(
        self,
        user: AuthenticatedUser,
        date_from: date | None,
        date_to: date | None,
    ) -> CalendarExportResult:
        self._record("create_calendar_export", user)
        return CalendarExportResult(
            filename="shiftmate-schedule.ics",
            media_type="text/calendar; charset=utf-8",
            content="BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n",
        )


async def test_six_tools_are_typed_read_only_and_expose_no_owner_or_sql() -> None:
    server = build_mcp_server(
        Settings(),
        operations=FakeOperations(),
        token_verifier=SyntheticTokenVerifier(),
        principal_provider=StaticPrincipal(),
    )

    tools = await server.list_tools()

    assert [tool.name for tool in tools] == [
        "get_shifts",
        "calculate_work_hours",
        "get_payroll_summary",
        "search_work_policy",
        "analyze_schedule_compliance",
        "create_calendar_export",
    ]
    for tool in tools:
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
        assert tool.output_schema is not None
        serialized = str(tool.input_schema).casefold()
        assert "owner" not in serialized
        assert "sql" not in serialized


async def test_tool_call_returns_structured_result_and_audits_hashed_owner(
    caplog: pytest.LogCaptureFixture,
) -> None:
    operations = FakeOperations()
    server = build_mcp_server(
        Settings(),
        operations=operations,
        token_verifier=SyntheticTokenVerifier(),
        principal_provider=StaticPrincipal(),
    )
    caplog.set_level("INFO", logger="shiftmate.mcp.audit")

    async with Client(server) as client:
        result = await client.call_tool(
            "calculate_work_hours",
            {"date_from": str(DATE_FROM), "date_to": str(DATE_TO)},
        )

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["total_paid_hours"] == "14.5"
    assert operations.calls == [("calculate_work_hours", USER.id)]
    messages = [
        record.message
        for record in caplog.records
        if record.name == "shiftmate.mcp.audit"
    ]
    assert messages, "Expected a structured shiftmate.mcp.audit log"
    audit = messages[-1]
    assert '"outcome": "success"' in audit
    assert str(USER.id) not in audit
    assert "synthetic-user-token" not in audit


async def test_unauthorized_in_process_tool_call_is_rejected() -> None:
    server = build_mcp_server(
        Settings(),
        operations=FakeOperations(),
        token_verifier=SyntheticTokenVerifier(),
        principal_provider=RejectingPrincipal(),
    )

    with pytest.raises(ToolError, match="UNAUTHORIZED"):
        await server.call_tool("get_shifts", {})


async def test_http_requires_bearer_and_is_stateless_across_server_restart() -> None:
    response_headers: list[httpx2.Headers] = []

    async def capture_headers(response: httpx2.Response) -> None:
        response_headers.append(response.headers)

    for _ in range(2):
        operations = FakeOperations()
        server = build_mcp_server(
            Settings(),
            operations=operations,
            token_verifier=SyntheticTokenVerifier(),
        )
        app = server.streamable_http_app(
            streamable_http_path="/mcp",
            json_response=True,
            stateless_http=True,
            transport_security=TransportSecuritySettings(
                allowed_hosts=["test"], allowed_origins=["http://test"]
            ),
        )
        unauthorized_transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=unauthorized_transport, base_url="http://test"
        ) as client:
            response = await client.post("/mcp", json={})
        assert response.status_code == 401

        transport = httpx2.ASGITransport(app=app)
        async with (
            app.router.lifespan_context(app),
            httpx2.AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={"Authorization": "Bearer synthetic-user-token"},
                event_hooks={"response": [capture_headers]},
            ) as http_client,
        ):
            connection = streamable_http_client(
                "http://test/mcp", http_client=http_client
            )
            async with Client(connection) as client:
                result = await client.call_tool("get_shifts", {})
        assert result.is_error is False
        assert operations.calls == [("get_shifts", USER.id)]

    assert response_headers
    assert all("mcp-session-id" not in headers for headers in response_headers)


class EmptyShiftRepository:
    def list_ids(self, connection: Connection) -> list[UUID]:
        return []

    def get_profile_timezone(self, connection: Connection) -> str | None:
        return "Asia/Taipei"

    def list_shifts(
        self,
        connection: Connection,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[object]:
        return []


class StaticProfileRepository:
    def get_preferences(self, connection: Connection) -> ProfilePreferences:
        return ProfilePreferences("Asia/Taipei", "TWD")


class EmptyRateRepository:
    def list_pay_rates(self, connection: Connection) -> list[object]:
        return []


class InProcessDatabaseOperations(DatabaseMcpOperations):
    async def _run(
        self,
        user: AuthenticatedUser,
        operation: Callable[[Connection], TestResultT],
    ) -> TestResultT:
        del user
        return operation(cast(Connection, object()))


async def test_mcp_and_rest_adapters_share_shift_and_analytics_services() -> None:
    shifts = cast(ShiftRepository, EmptyShiftRepository())
    analytics = AnalyticsService(
        cast(ProfileRepository, StaticProfileRepository()),
        shifts,
        cast(PayRateRepository, EmptyRateRepository()),
    )
    operations = InProcessDatabaseOperations(Settings())
    operations.shift_service = ShiftService(shifts)
    operations.analytics_service = analytics

    rest_shift_records = operations.shift_service.list_shifts(
        cast(Connection, object()), DATE_FROM, DATE_TO
    )
    rest_summary = analytics.get_summary(cast(Connection, object()), DATE_FROM, DATE_TO)
    mcp_shifts = await operations.get_shifts(USER, DATE_FROM, DATE_TO)
    mcp_hours = await operations.calculate_work_hours(USER, DATE_FROM, DATE_TO)

    assert mcp_shifts.model_dump(mode="json") == {"shifts": []}
    assert rest_shift_records == []
    assert mcp_hours.total_paid_hours == rest_summary.total_paid_hours
    assert mcp_hours.weekly_hours == rest_summary.weekly_hours
