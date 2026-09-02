import json
from pathlib import Path

import httpx
import pytest

from backend.app.integrations.gemini import (
    GeminiExtractionError,
    GeminiScheduleExtractor,
)


def test_adapter_sends_structured_schema_and_validates_response(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "synthetic.png"
    source.write_bytes(b"synthetic")
    captured: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        captured.update(kwargs)
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "items": [
                                                {
                                                    "work_date": "2026-09-03",
                                                    "start_time": "09:00:00",
                                                    "end_time": "17:00:00",
                                                    "crosses_midnight": False,
                                                    "break_minutes": 30,
                                                    "shift_type": "day",
                                                    "notes": None,
                                                    "needs_review": False,
                                                    "warnings": [],
                                                }
                                            ]
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    result = GeminiScheduleExtractor("secret", "gemini-2.5-flash", 5).extract(
        source, "image/png", "Asia/Taipei"
    )

    assert result.items[0].shift_type == "day"
    assert captured["headers"] == {"x-goog-api-key": "secret"}
    payload = captured["json"]
    assert isinstance(payload, dict)
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert "responseJsonSchema" in payload["generationConfig"]


def test_adapter_maps_quota_error_to_safe_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "synthetic.png"
    source.write_bytes(b"synthetic")

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(429, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(GeminiExtractionError, match="GEMINI_QUOTA_EXHAUSTED"):
        GeminiScheduleExtractor("secret", "gemini-2.5-flash", 5).extract(
            source, "image/png", "Asia/Taipei"
        )
