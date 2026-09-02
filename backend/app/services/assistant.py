import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import Connection

from backend.app.schemas.assistant import (
    AssistantIntent,
    AssistantQueryResponse,
    AssistantScheduleFacts,
    AssistantToolTrace,
)
from backend.app.schemas.policies import PolicyCitation
from backend.app.services.analytics import AnalyticsService
from backend.app.services.policies import PolicyEvidence

HYBRID_PROMPT_VERSION = "hybrid_compliance_v1"
UNSUPPORTED_ANSWER = "我目前只能回答班表、工時、預估薪資與已上傳規章相關問題。"


class IntentClassifier(Protocol):
    def classify(self, question: str) -> AssistantIntent: ...


class AssistantAnswerer(Protocol):
    model_name: str

    def answer_policy(self, question: str, evidence: list[PolicyEvidence]) -> str: ...

    def answer_hybrid(
        self,
        question: str,
        facts: AssistantScheduleFacts,
        evidence: list[PolicyEvidence],
        evaluation: "ComplianceEvaluation",
    ) -> str: ...


PolicyEvidenceLoader = Callable[[Connection, str], list[PolicyEvidence]]


class AssistantState(TypedDict, total=False):
    connection: Connection
    question: str
    normalized_question: str
    date_from: date
    date_to: date
    intent: AssistantIntent
    schedule_facts: AssistantScheduleFacts
    policy_evidence: list[PolicyEvidence]
    citations: list[PolicyCitation]
    evaluation: "ComplianceEvaluation"
    evidence_valid: bool
    answer: str
    refused: bool
    tools: list[AssistantToolTrace]
    prompt_version: str | None
    model_name: str | None


@dataclass(frozen=True, slots=True)
class ComplianceEvaluation:
    outcome: Literal["compliant", "non_compliant", "inconclusive"]
    maximum_consecutive_days: int | None
    observed_consecutive_days: int


class AssistantService:
    """Stateless LangGraph workflow over owner-scoped application services."""

    def __init__(
        self,
        analytics: AnalyticsService,
        policy_loader: PolicyEvidenceLoader,
        answerer: AssistantAnswerer,
        classifier: IntentClassifier | None = None,
    ) -> None:
        self.analytics = analytics
        self.policy_loader = policy_loader
        self.answerer = answerer
        self.classifier = classifier
        self.graph = self._build_graph()

    def query(
        self,
        connection: Connection,
        question: str,
        date_from: date,
        date_to: date,
    ) -> AssistantQueryResponse:
        if date_to < date_from:
            raise ValueError("date_to cannot be before date_from")
        if date_to - date_from > timedelta(days=365):
            raise ValueError("Assistant date range cannot exceed 366 days")
        result = self.graph.invoke(
            {
                "connection": connection,
                "question": question,
                "date_from": date_from,
                "date_to": date_to,
                "tools": [],
            }
        )
        return AssistantQueryResponse(
            answer=result["answer"],
            intent=result["intent"],
            refused=result["refused"],
            citations=result.get("citations", []),
            schedule_facts=result.get("schedule_facts"),
            tools=result.get("tools", []),
            prompt_version=result.get("prompt_version"),
            model_name=result.get("model_name"),
        )

    def _build_graph(self) -> Any:
        builder = StateGraph(AssistantState)
        builder.add_node("normalize_question", self._normalize_question)
        builder.add_node("route_intent", self._route_intent)
        builder.add_node("schedule_query", self._schedule_query)
        builder.add_node("policy_query", self._policy_query)
        builder.add_node("hybrid_query", self._hybrid_query)
        builder.add_node("unsupported", self._unsupported)
        builder.add_node("validate_evidence", self._validate_evidence)
        builder.add_node("compose_answer", self._compose_answer)
        builder.add_edge(START, "normalize_question")
        builder.add_edge("normalize_question", "route_intent")
        builder.add_conditional_edges(
            "route_intent",
            lambda state: state["intent"],
            {
                "schedule": "schedule_query",
                "policy": "policy_query",
                "hybrid": "hybrid_query",
                "unsupported": "unsupported",
            },
        )
        for node in ("schedule_query", "policy_query", "hybrid_query", "unsupported"):
            builder.add_edge(node, "validate_evidence")
        builder.add_edge("validate_evidence", "compose_answer")
        builder.add_edge("compose_answer", END)
        return builder.compile()

    @staticmethod
    def _normalize_question(state: AssistantState) -> AssistantState:
        normalized = " ".join(state["question"].strip().split())
        return {"normalized_question": normalized}

    def _route_intent(self, state: AssistantState) -> AssistantState:
        question = state["normalized_question"]
        intent = deterministic_route(question)
        if intent is None:
            intent = (
                self.classifier.classify(question) if self.classifier else "unsupported"
            )
        return {"intent": intent}

    def _schedule_query(self, state: AssistantState) -> AssistantState:
        facts = self._load_schedule_facts(state)
        return {
            "schedule_facts": facts,
            "tools": [AssistantToolTrace(name="schedule_summary", status="used")],
        }

    def _policy_query(self, state: AssistantState) -> AssistantState:
        evidence = self.policy_loader(state["connection"], state["normalized_question"])
        return {
            "policy_evidence": evidence,
            "citations": [item.citation for item in evidence],
            "tools": [
                AssistantToolTrace(
                    name="policy_retrieval",
                    status="used" if evidence else "insufficient",
                )
            ],
        }

    def _hybrid_query(self, state: AssistantState) -> AssistantState:
        facts = self._load_schedule_facts(state)
        evidence = self.policy_loader(state["connection"], state["normalized_question"])
        evaluation = evaluate_consecutive_days(facts, evidence)
        return {
            "schedule_facts": facts,
            "policy_evidence": evidence,
            "citations": [item.citation for item in evidence],
            "evaluation": evaluation,
            "tools": [
                AssistantToolTrace(name="schedule_summary", status="used"),
                AssistantToolTrace(
                    name="policy_retrieval",
                    status="used" if evidence else "insufficient",
                ),
                AssistantToolTrace(
                    name="rule_evaluator",
                    status=(
                        "used"
                        if evaluation.outcome != "inconclusive"
                        else "insufficient"
                    ),
                ),
            ],
        }

    @staticmethod
    def _unsupported(state: AssistantState) -> AssistantState:
        del state
        return {"answer": UNSUPPORTED_ANSWER, "refused": True, "tools": []}

    @staticmethod
    def _validate_evidence(state: AssistantState) -> AssistantState:
        intent = state["intent"]
        if intent == "unsupported":
            valid = False
        elif intent == "schedule":
            valid = "schedule_facts" in state
        elif intent == "policy":
            valid = bool(state.get("policy_evidence"))
        else:
            valid = bool(
                state.get("schedule_facts")
                and state.get("policy_evidence")
                and state.get("evaluation")
                and state["evaluation"].outcome != "inconclusive"
            )
        return {"evidence_valid": valid}

    def _compose_answer(self, state: AssistantState) -> AssistantState:
        intent = state["intent"]
        if intent == "unsupported":
            return {}
        if not state["evidence_valid"]:
            if intent == "policy":
                answer = "上傳的規章中沒有足夠資料可以回答這個問題。"
            elif intent == "hybrid":
                answer = (
                    "資料不足，無法判定是否符合規章；需要該期間班表、"
                    "可引用的規章與可解析的規則。"
                )
            else:
                answer = "目前沒有足夠的班表資料可以回答這個問題。"
            return {"answer": answer, "refused": True}
        if intent == "schedule":
            facts = state["schedule_facts"]
            return {
                "answer": (
                    f"{facts.date_from} 至 {facts.date_to} 共 {facts.shift_count} 班，"
                    f"總工時 {facts.total_paid_hours} 小時，預估薪資 "
                    f"{facts.currency} {facts.estimated_pay}；最長連續工作 "
                    f"{facts.longest_consecutive_days} 天。"
                ),
                "refused": False,
                "prompt_version": None,
                "model_name": None,
            }
        if intent == "policy":
            return {
                "answer": self.answerer.answer_policy(
                    state["normalized_question"], state["policy_evidence"]
                ),
                "refused": False,
                "prompt_version": "rag_answer_v1",
                "model_name": self.answerer.model_name,
            }
        return {
            "answer": self.answerer.answer_hybrid(
                state["normalized_question"],
                state["schedule_facts"],
                state["policy_evidence"],
                state["evaluation"],
            ),
            "refused": False,
            "prompt_version": HYBRID_PROMPT_VERSION,
            "model_name": self.answerer.model_name,
        }

    def _load_schedule_facts(self, state: AssistantState) -> AssistantScheduleFacts:
        summary = self.analytics.get_summary(
            state["connection"], state["date_from"], state["date_to"]
        )
        return AssistantScheduleFacts.model_validate(summary, from_attributes=True)


def deterministic_route(question: str) -> AssistantIntent | None:
    lowered = question.casefold()
    blocked_terms = (
        "raw sql",
        "select ",
        "insert ",
        "update ",
        "delete ",
        "刪除班",
        "新增班",
        "修改班",
        "寫入班",
    )
    if any(term in lowered for term in blocked_terms):
        return "unsupported"
    schedule = any(
        term in lowered
        for term in (
            "班表",
            "我的班",
            "上班",
            "排班",
            "工時",
            "薪資",
            "薪水",
            "時數",
            "幾班",
            "shift",
            "hours",
            "payroll",
        )
    )
    policy = any(
        term in lowered
        for term in (
            "規章",
            "規定",
            "政策",
            "手冊",
            "休息時間",
            "連續工作",
            "合規",
            "違反",
            "policy",
            "rule",
        )
    )
    if schedule and policy:
        return "hybrid"
    if schedule:
        return "schedule"
    if policy:
        return "policy"
    if any(term in lowered for term in ("天氣", "新聞", "股票", "寫入", "刪除班")):
        return "unsupported"
    return None


def evaluate_consecutive_days(
    facts: AssistantScheduleFacts, evidence: list[PolicyEvidence]
) -> ComplianceEvaluation:
    limits: list[int] = []
    patterns = (
        r"不得連續工作(?:超過)?\s*([0-9一二三四五六七八九十]+)\s*天",
        r"連續工作(?:上限|最多)\s*([0-9一二三四五六七八九十]+)\s*天",
    )
    for item in evidence:
        for pattern in patterns:
            for match in re.finditer(pattern, item.text):
                parsed = _parse_small_integer(match.group(1))
                if parsed is not None:
                    limits.append(parsed)
    maximum = limits[0] if limits and len(set(limits)) == 1 else None
    if maximum is None or facts.shift_count == 0:
        outcome: Literal["compliant", "non_compliant", "inconclusive"] = "inconclusive"
    elif facts.longest_consecutive_days > maximum:
        outcome = "non_compliant"
    else:
        outcome = "compliant"
    return ComplianceEvaluation(outcome, maximum, facts.longest_consecutive_days)


def _parse_small_integer(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    numerals = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }
    return numerals.get(value)
