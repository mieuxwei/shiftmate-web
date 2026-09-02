from datetime import date
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import Connection

from backend.app.schemas.assistant import AssistantScheduleFacts
from backend.app.schemas.policies import PolicyCitation
from backend.app.services.analytics import AnalyticsService, AnalyticsSummary
from backend.app.services.assistant import (
    AssistantService,
    ComplianceEvaluation,
    deterministic_route,
)
from backend.app.services.policies import PolicyEvidence

CONNECTION = cast(Connection, object())
DATE_FROM = date(2026, 9, 1)
DATE_TO = date(2026, 9, 7)


class FakeAnalytics:
    def __init__(self, shift_count: int = 6, consecutive_days: int = 6) -> None:
        self.shift_count = shift_count
        self.consecutive_days = consecutive_days
        self.calls = 0

    def get_summary(
        self, connection: Connection, date_from: date, date_to: date
    ) -> AnalyticsSummary:
        self.calls += 1
        return AnalyticsSummary(
            date_from=date_from,
            date_to=date_to,
            timezone="Asia/Taipei",
            currency="TWD",
            shift_count=self.shift_count,
            total_paid_hours=Decimal("42.0"),
            estimated_pay=Decimal("8400.00"),
            shift_type_counts={"day": self.shift_count},
            weekly_hours={DATE_FROM: Decimal("42.0")},
            longest_consecutive_days=self.consecutive_days,
        )


class FakeAnswerer:
    model_name = "synthetic-model"

    def answer_policy(self, question: str, evidence: list[PolicyEvidence]) -> str:
        return "規章規定不得連續工作超過五天。"

    def answer_hybrid(
        self,
        question: str,
        facts: AssistantScheduleFacts,
        evidence: list[PolicyEvidence],
        evaluation: ComplianceEvaluation,
    ) -> str:
        return (
            f"最長連續工作 {facts.longest_consecutive_days} 天，規章上限 "
            f"{evaluation.maximum_consecutive_days} 天；結果為 {evaluation.outcome}。"
        )


def policy_evidence(text: str = "員工不得連續工作超過五天。") -> PolicyEvidence:
    return PolicyEvidence(
        text=text,
        citation=PolicyCitation(
            document_id=UUID(int=1),
            chunk_id=UUID(int=2),
            title="合成工作規章",
            page_number=3,
            excerpt=text,
        ),
    )


def assistant(
    *,
    evidence: list[PolicyEvidence] | None = None,
    shift_count: int = 6,
    consecutive_days: int = 6,
) -> tuple[AssistantService, FakeAnalytics]:
    analytics = FakeAnalytics(shift_count, consecutive_days)
    service = AssistantService(
        cast(AnalyticsService, analytics),
        lambda connection, question: (
            evidence if evidence is not None else [policy_evidence()]
        ),
        FakeAnswerer(),
    )
    return service, analytics


def test_deterministic_router_covers_all_four_routes_and_blocks_sql() -> None:
    assert deterministic_route("我這週總工時與薪資是多少？") == "schedule"
    assert deterministic_route("規章的休息時間如何規定？") == "policy"
    assert deterministic_route("我的班表有違反連續工作規定嗎？") == "hybrid"
    assert deterministic_route("今天的天氣如何？") == "unsupported"
    assert deterministic_route("請執行 SELECT * FROM shifts") == "unsupported"
    assert deterministic_route("可以幫我嗎？") is None


def test_schedule_route_uses_only_deterministic_analytics() -> None:
    service, analytics = assistant()
    result = service.query(CONNECTION, "我這週總工時與薪資是多少？", DATE_FROM, DATE_TO)

    assert result.intent == "schedule"
    assert result.refused is False
    assert result.schedule_facts is not None
    assert result.schedule_facts.total_paid_hours == Decimal("42.0")
    assert result.schedule_facts.estimated_pay == Decimal("8400.00")
    assert result.model_name is None
    assert [tool.name for tool in result.tools] == ["schedule_summary"]
    assert analytics.calls == 1


def test_policy_and_hybrid_routes_preserve_database_citations() -> None:
    service, _ = assistant()
    policy = service.query(CONNECTION, "規章的連續工作規定是什麼？", DATE_FROM, DATE_TO)
    hybrid = service.query(
        CONNECTION, "我的班表有違反連續工作規定嗎？", DATE_FROM, DATE_TO
    )

    assert policy.intent == "policy"
    assert policy.citations[0].page_number == 3
    assert hybrid.intent == "hybrid"
    assert hybrid.refused is False
    assert hybrid.schedule_facts is not None
    assert hybrid.schedule_facts.longest_consecutive_days == 6
    assert hybrid.citations[0].document_id == UUID(int=1)
    assert "non_compliant" in hybrid.answer
    assert [tool.name for tool in hybrid.tools] == [
        "schedule_summary",
        "policy_retrieval",
        "rule_evaluator",
    ]


def test_hybrid_refuses_without_both_fact_and_parseable_policy_evidence() -> None:
    missing_policy, _ = assistant(evidence=[])
    no_rule, _ = assistant(evidence=[policy_evidence("請遵守公司規章。")])
    no_shifts, _ = assistant(shift_count=0, consecutive_days=0)

    for service in (missing_policy, no_rule, no_shifts):
        result = service.query(
            CONNECTION, "我的班表有違反連續工作規定嗎？", DATE_FROM, DATE_TO
        )
        assert result.intent == "hybrid"
        assert result.refused is True
        assert "無法判定" in result.answer


def test_hybrid_refuses_conflicting_policy_thresholds() -> None:
    service, _ = assistant(
        evidence=[
            policy_evidence("員工不得連續工作超過五天。"),
            policy_evidence("員工不得連續工作超過六天。"),
        ]
    )

    result = service.query(
        CONNECTION, "我的班表有違反連續工作規定嗎？", DATE_FROM, DATE_TO
    )

    assert result.refused is True
    assert "無法判定" in result.answer


def test_graph_has_no_cross_request_conversational_memory() -> None:
    service, analytics = assistant()
    first = service.query(CONNECTION, "這週有幾班？", DATE_FROM, DATE_TO)
    second = service.query(CONNECTION, "天氣如何？", DATE_FROM, DATE_TO)

    assert first.intent == "schedule"
    assert second.intent == "unsupported"
    assert second.schedule_facts is None
    assert second.citations == []
    assert analytics.calls == 1
