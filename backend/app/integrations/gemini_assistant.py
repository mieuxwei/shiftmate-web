import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from backend.app.integrations.gemini_rag import (
    RAG_PROMPT_PATH,
    GeminiRagError,
    _post_json,
)
from backend.app.schemas.assistant import AssistantIntent, AssistantScheduleFacts
from backend.app.services.assistant import ComplianceEvaluation
from backend.app.services.policies import PolicyEvidence

PROMPT_DIR = Path(__file__).parents[1] / "ai" / "prompts"


class GeminiAssistantAdapter:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        timeout_seconds: float,
        before_request: Callable[[], None] | None = None,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.before_request = before_request

    def classify(self, question: str) -> AssistantIntent:
        body = self._generate(
            (PROMPT_DIR / "intent_router_v1.md").read_text(encoding="utf-8"),
            {"question": question},
            max_tokens=40,
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "intent": {
                        "type": "STRING",
                        "enum": ["schedule", "policy", "hybrid", "unsupported"],
                    }
                },
                "required": ["intent"],
            },
        )
        try:
            intent = json.loads(body)["intent"]
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise GeminiRagError("GEMINI_INVALID_RESPONSE") from error
        if intent not in {"schedule", "policy", "hybrid", "unsupported"}:
            raise GeminiRagError("GEMINI_INVALID_RESPONSE")
        return cast(AssistantIntent, intent)

    def answer_policy(self, question: str, evidence: list[PolicyEvidence]) -> str:
        return self._generate(
            RAG_PROMPT_PATH.read_text(encoding="utf-8"),
            {
                "question": question,
                "untrusted_evidence": [
                    _evidence(item, index) for index, item in enumerate(evidence)
                ],
            },
            max_tokens=700,
        )

    def answer_hybrid(
        self,
        question: str,
        facts: AssistantScheduleFacts,
        evidence: list[PolicyEvidence],
        evaluation: ComplianceEvaluation,
    ) -> str:
        return self._generate(
            (PROMPT_DIR / "hybrid_compliance_v1.md").read_text(encoding="utf-8"),
            {
                "question": question,
                "deterministic_schedule_facts": facts.model_dump(mode="json"),
                "deterministic_rule_evaluation": {
                    "outcome": evaluation.outcome,
                    "maximum_consecutive_days": evaluation.maximum_consecutive_days,
                    "observed_consecutive_days": evaluation.observed_consecutive_days,
                },
                "untrusted_policy_evidence": [
                    _evidence(item, index) for index, item in enumerate(evidence)
                ],
            },
            max_tokens=700,
        )

    def _generate(
        self,
        system_prompt: str,
        payload_data: dict[str, object],
        *,
        max_tokens: int,
        response_schema: dict[str, object] | None = None,
    ) -> str:
        generation_config: dict[str, object] = {
            "temperature": 0,
            "maxOutputTokens": max_tokens,
        }
        if response_schema is not None:
            generation_config.update(
                {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": response_schema,
                }
            )
        if self.before_request is not None:
            self.before_request()
        body = _post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent",
            self.api_key,
            {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": (
                                    "INPUT_JSON_BEGIN\n"
                                    f"{json.dumps(payload_data, ensure_ascii=False)}\n"
                                    "INPUT_JSON_END"
                                )
                            }
                        ],
                    }
                ],
                "generationConfig": generation_config,
            },
            self.timeout_seconds,
        )
        try:
            raw_answer = body["candidates"][0]["content"]["parts"][0]["text"]
            if not isinstance(raw_answer, str):
                raise TypeError
            answer = raw_answer.strip()
        except (KeyError, IndexError, TypeError, AttributeError) as error:
            raise GeminiRagError("GEMINI_INVALID_RESPONSE") from error
        if not answer:
            raise GeminiRagError("GEMINI_INVALID_RESPONSE")
        return answer


def _evidence(item: PolicyEvidence, index: int) -> dict[str, Any]:
    return {
        "label": f"source_{index + 1}",
        "title": item.citation.title,
        "page_number": item.citation.page_number,
        "text": item.text,
    }
