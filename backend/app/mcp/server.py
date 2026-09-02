import hashlib
import json
import logging
import os
import time
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Annotated, TypeVar

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import AnyHttpUrl, BaseModel, Field
from starlette.applications import Starlette

from backend.app.core.auth import AuthenticatedUser
from backend.app.core.quotas import QuotaExceededError
from backend.app.core.settings import Settings, get_settings
from backend.app.integrations.gemini_rag import GeminiRagError
from backend.app.mcp.auth import (
    McpAuthenticationError,
    PrincipalProvider,
    SupabaseMcpTokenVerifier,
    TransportPrincipalProvider,
)
from backend.app.mcp.operations import (
    DatabaseMcpOperations,
    McpOperationError,
    McpOperations,
)
from backend.app.mcp.schemas import (
    CalendarExportResult,
    ComplianceAnalysisResult,
    PayrollSummaryResult,
    PolicySearchResult,
    ShiftListResult,
    WorkHoursResult,
)
from backend.app.services.analytics import (
    AnalyticsCalculationError,
    AnalyticsServiceError,
)
from backend.app.services.calendar_exports import CalendarExportError
from backend.app.services.shifts import ProfileNotFoundError, ShiftServiceError

logger = logging.getLogger("shiftmate.mcp.audit")
ResultT = TypeVar("ResultT", bound=BaseModel)
READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


def build_mcp_server(
    settings: Settings,
    *,
    operations: McpOperations | None = None,
    token_verifier: TokenVerifier | None = None,
    principal_provider: PrincipalProvider | None = None,
    stdio_access_token: str | None = None,
) -> MCPServer[None]:
    verifier = token_verifier or SupabaseMcpTokenVerifier(settings)
    principals = principal_provider or TransportPrincipalProvider(
        verifier, stdio_access_token
    )
    service = operations or DatabaseMcpOperations(settings)
    server: MCPServer[None] = MCPServer(
        "shiftmate-web",
        title="ShiftMate Web",
        description="Owner-scoped, read-only schedule and work-policy tools.",
        instructions=(
            "All tools are read-only. Estimated pay is informational and is not "
            "legal, HR, or payroll advice."
        ),
        version="0.1.0",
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(
                f"{str(settings.supabase_url).rstrip('/')}/auth/v1"
                if settings.supabase_url
                else "http://localhost/auth/v1"
            ),
            resource_server_url=None,
            required_scopes=["shiftmate:read"],
        ),
        token_verifier=verifier,
    )

    async def invoke(
        name: str,
        context: Context[None, object],
        operation: Callable[[AuthenticatedUser], Awaitable[ResultT]],
    ) -> ResultT:
        started = time.monotonic()
        try:
            user = await principals.require_user()
        except McpAuthenticationError as error:
            _audit(name, None, "unauthorized", context, started)
            raise ToolError("UNAUTHORIZED") from error
        try:
            result = await operation(user)
        except Exception as error:
            code = _safe_error_code(error)
            _audit(name, user, code, context, started)
            if code == "MCP_TOOL_FAILED":
                logger.exception("MCP tool failed unexpectedly", extra={"tool": name})
            raise ToolError(code) from error
        _audit(name, user, "success", context, started)
        return result

    @server.tool(
        name="get_shifts",
        description="List the authenticated owner's confirmed shifts in a date range.",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def get_shifts(
        context: Context[None, object],
        date_from: Annotated[
            date | None, Field(description="Inclusive start date")
        ] = None,
        date_to: Annotated[date | None, Field(description="Inclusive end date")] = None,
    ) -> ShiftListResult:
        return await invoke(
            "get_shifts",
            context,
            lambda user: service.get_shifts(user, date_from, date_to),
        )

    @server.tool(
        name="calculate_work_hours",
        description="Calculate deterministic paid work hours for a bounded date range.",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def calculate_work_hours(
        context: Context[None, object], date_from: date, date_to: date
    ) -> WorkHoursResult:
        return await invoke(
            "calculate_work_hours",
            context,
            lambda user: service.calculate_work_hours(user, date_from, date_to),
        )

    @server.tool(
        name="get_payroll_summary",
        description=(
            "Return a deterministic estimated-pay summary; never payroll advice."
        ),
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def get_payroll_summary(
        context: Context[None, object], date_from: date, date_to: date
    ) -> PayrollSummaryResult:
        return await invoke(
            "get_payroll_summary",
            context,
            lambda user: service.get_payroll_summary(user, date_from, date_to),
        )

    @server.tool(
        name="search_work_policy",
        description="Search only the authenticated owner's indexed policy evidence.",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def search_work_policy(
        context: Context[None, object],
        question: Annotated[str, Field(min_length=2, max_length=1000)],
    ) -> PolicySearchResult:
        return await invoke(
            "search_work_policy",
            context,
            lambda user: service.search_work_policy(user, question),
        )

    @server.tool(
        name="analyze_schedule_compliance",
        description=(
            "Analyze schedule facts against owner-scoped policy evidence and refuse "
            "when evidence is insufficient."
        ),
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def analyze_schedule_compliance(
        context: Context[None, object],
        question: Annotated[str, Field(min_length=2, max_length=1000)],
        date_from: date,
        date_to: date,
    ) -> ComplianceAnalysisResult:
        return await invoke(
            "analyze_schedule_compliance",
            context,
            lambda user: service.analyze_schedule_compliance(
                user, question, date_from, date_to
            ),
        )

    @server.tool(
        name="create_calendar_export",
        description="Render an in-memory ICS export without creating calendar events.",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def create_calendar_export(
        context: Context[None, object],
        date_from: Annotated[
            date | None, Field(description="Inclusive start date")
        ] = None,
        date_to: Annotated[date | None, Field(description="Inclusive end date")] = None,
    ) -> CalendarExportResult:
        return await invoke(
            "create_calendar_export",
            context,
            lambda user: service.create_calendar_export(user, date_from, date_to),
        )

    return server


def build_http_mcp_app(settings: Settings) -> Starlette:
    server = build_mcp_server(settings)
    return server.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        max_request_body_size=64 * 1024,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=settings.mcp_allowed_hosts,
            allowed_origins=settings.mcp_allowed_origins,
        ),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    server = build_mcp_server(
        settings,
        stdio_access_token=os.environ.get("SHIFTMATE_MCP_ACCESS_TOKEN"),
    )
    server.run("stdio")


def _safe_error_code(error: Exception) -> str:
    if isinstance(error, McpOperationError):
        return error.code
    if isinstance(error, GeminiRagError):
        return error.code
    if isinstance(error, QuotaExceededError):
        return error.code
    if isinstance(error, ProfileNotFoundError):
        return "PROFILE_NOT_FOUND"
    if isinstance(
        error,
        (
            ShiftServiceError,
            AnalyticsServiceError,
            AnalyticsCalculationError,
            CalendarExportError,
            ValueError,
        ),
    ):
        return "INVALID_REQUEST"
    return "MCP_TOOL_FAILED"


def _audit(
    tool: str,
    user: AuthenticatedUser | None,
    outcome: str,
    context: Context[None, object],
    started: float,
) -> None:
    owner_ref = hashlib.sha256(str(user.id).encode()).hexdigest()[:16] if user else None
    try:
        request_id = context.request_id
    except (RuntimeError, ValueError):
        request_id = "unavailable"
    logger.info(
        json.dumps(
            {
                "event": "mcp_tool_call",
                "tool": tool,
                "owner_ref": owner_ref,
                "outcome": outcome,
                "request_id": request_id,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
