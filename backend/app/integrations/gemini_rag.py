import json
import math
from pathlib import Path
from typing import Any

import httpx
from langchain_core.embeddings import Embeddings

RAG_PROMPT_VERSION = "rag_answer_v1"
RAG_PROMPT_PATH = (
    Path(__file__).parents[1] / "ai" / "prompts" / f"{RAG_PROMPT_VERSION}.md"
)


class GeminiRagError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class GeminiEmbeddings(Embeddings):
    def __init__(
        self,
        api_key: str,
        model_name: str,
        timeout_seconds: float,
        dimensions: int = 768,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text, "RETRIEVAL_DOCUMENT") for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text, "RETRIEVAL_QUERY")

    def _embed(self, text: str, task_type: str) -> list[float]:
        payload: dict[str, Any] = {
            "model": f"models/{self.model_name}",
            "content": {"parts": [{"text": text}]},
            "embedContentConfig": {
                "taskType": task_type,
                "outputDimensionality": self.dimensions,
                "autoTruncate": False,
            },
        }
        body = _post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:embedContent",
            self.api_key,
            payload,
            self.timeout_seconds,
        )
        try:
            values = [float(value) for value in body["embedding"]["values"]]
        except (KeyError, TypeError, ValueError) as error:
            raise GeminiRagError("GEMINI_INVALID_RESPONSE") from error
        if len(values) != self.dimensions or not all(math.isfinite(v) for v in values):
            raise GeminiRagError("GEMINI_INVALID_RESPONSE")
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0:
            raise GeminiRagError("GEMINI_INVALID_RESPONSE")
        return [value / norm for value in values]


class GeminiGroundedAnswerer:
    prompt_version = RAG_PROMPT_VERSION

    def __init__(self, api_key: str, model_name: str, timeout_seconds: float) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    def answer(self, question: str, evidence: list[dict[str, Any]]) -> str:
        prompt = RAG_PROMPT_PATH.read_text(encoding="utf-8")
        evidence_json = json.dumps(evidence, ensure_ascii=False)
        payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": prompt}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                f"Question:\n{question}\n\n"
                                "UNTRUSTED_EVIDENCE_JSON_BEGIN\n"
                                f"{evidence_json}\n"
                                "UNTRUSTED_EVIDENCE_JSON_END"
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 700},
        }
        body = _post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent",
            self.api_key,
            payload,
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


def _post_json(
    url: str, api_key: str, payload: dict[str, object], timeout_seconds: float
) -> dict[str, Any]:
    try:
        response = httpx.post(
            url,
            headers={"x-goog-api-key": api_key},
            json=payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise TypeError
        return body
    except httpx.TimeoutException as error:
        raise GeminiRagError("GEMINI_TIMEOUT") from error
    except httpx.RequestError as error:
        raise GeminiRagError("GEMINI_UNAVAILABLE") from error
    except httpx.HTTPStatusError as error:
        code = (
            "GEMINI_QUOTA_EXHAUSTED"
            if error.response.status_code == 429
            else "GEMINI_UNAVAILABLE"
        )
        raise GeminiRagError(code) from error
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise GeminiRagError("GEMINI_INVALID_RESPONSE") from error
