import base64
import json
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import httpx

from backend.app.schemas.imports import ScheduleExtraction

PROMPT_VERSION = "schedule_extraction_v1"
PROMPT_PATH = Path(__file__).parents[1] / "ai" / "prompts" / f"{PROMPT_VERSION}.md"


class GeminiExtractionError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ScheduleExtractor(Protocol):
    model_name: str
    prompt_version: str

    def extract(
        self, path: Path, media_type: str, timezone: str
    ) -> ScheduleExtraction: ...


class GeminiScheduleExtractor:
    prompt_version = PROMPT_VERSION

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

    def extract(self, path: Path, media_type: str, timezone: str) -> ScheduleExtraction:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
        schema = ScheduleExtraction.model_json_schema(mode="serialization")
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{prompt}\nOwner timezone: {timezone}"},
                        {
                            "inline_data": {
                                "mime_type": media_type,
                                "data": base64.b64encode(path.read_bytes()).decode(),
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
                "temperature": 0,
            },
        }
        try:
            if self.before_request is not None:
                self.before_request()
            response = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent",
                headers={"x-goog-api-key": self.api_key},
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            raw_text = body["candidates"][0]["content"]["parts"][0]["text"]
            return ScheduleExtraction.model_validate_json(raw_text)
        except httpx.TimeoutException as error:
            raise GeminiExtractionError("GEMINI_TIMEOUT") from error
        except httpx.HTTPStatusError as error:
            code = (
                "GEMINI_QUOTA_EXHAUSTED"
                if error.response.status_code == 429
                else "GEMINI_UNAVAILABLE"
            )
            raise GeminiExtractionError(code) from error
        except (
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
            ValueError,
        ) as error:
            raise GeminiExtractionError("GEMINI_INVALID_RESPONSE") from error
