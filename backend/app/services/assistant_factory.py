from typing import cast

from langchain_core.embeddings import Embeddings
from sqlalchemy import Connection

from backend.app.integrations.gemini_assistant import GeminiAssistantAdapter
from backend.app.integrations.gemini_rag import GeminiRagError
from backend.app.services.analytics import AnalyticsService
from backend.app.services.assistant import (
    AssistantAnswerer,
    AssistantService,
    IntentClassifier,
)
from backend.app.services.policies import PolicyEvidence, PolicyService


class UnavailableAssistantModel:
    model_name = "unavailable"

    def answer_policy(self, question: str, evidence: list[PolicyEvidence]) -> str:
        del question, evidence
        raise GeminiRagError("GEMINI_NOT_CONFIGURED")

    def answer_hybrid(self, *args: object) -> str:
        del args
        raise GeminiRagError("GEMINI_NOT_CONFIGURED")


def build_assistant_service(
    analytics: AnalyticsService,
    policies: PolicyService,
    embeddings: Embeddings | None,
    model: GeminiAssistantAdapter | None,
    *,
    top_k: int,
    score_threshold: float,
) -> AssistantService:
    def load_policy_evidence(
        connection: Connection, question: str
    ) -> list[PolicyEvidence]:
        if embeddings is None:
            raise GeminiRagError("GEMINI_NOT_CONFIGURED")
        return policies.retrieve_evidence(
            connection,
            question,
            embeddings,
            top_k,
            score_threshold,
        )

    return AssistantService(
        analytics,
        load_policy_evidence,
        cast(AssistantAnswerer, model) if model else UnavailableAssistantModel(),
        classifier=cast(IntentClassifier, model) if model else None,
    )
