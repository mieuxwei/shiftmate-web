import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


def load_evaluator() -> ModuleType:
    path = Path("evals/ocr/evaluate.py")
    spec = importlib.util.spec_from_file_location("ocr_evaluate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_synthetic_ocr_fixture_covers_required_cases_and_metrics() -> None:
    root = Path("evals/ocr")
    cases = json.loads((root / "cases.json").read_text(encoding="utf-8"))
    predictions = json.loads(
        (root / "synthetic_predictions.json").read_text(encoding="utf-8")
    )
    tags = {tag for case in cases for tag in case["tags"]}
    assert {
        "clear-image",
        "shadow",
        "skew",
        "overnight",
        "rest-day",
        "multiple-people",
        "multiple-dates",
        "mark",
        "ambiguous",
    } <= tags

    metrics = load_evaluator().evaluate(cases, predictions)
    assert metrics["sample_count"] == 9
    assert metrics["expected_item_count"] == 9
    assert metrics["predicted_item_count"] == 8
    assert metrics["date_exact_match"] == 8 / 9
    assert metrics["time_exact_match"] == 7 / 9
    assert metrics["missing_shift_rate"] == 1 / 9
    assert metrics["extra_shift_rate"] == 0.0
    assert metrics["schema_valid_rate"] == 1.0
    assert metrics["needs_review_recall"] == 4 / 5
    assert metrics["failure_count"] == 3
    assert {failure["id"] for failure in metrics["failures"]} == {
        "skewed",
        "multiple-dates",
        "illegible",
    }

    with pytest.raises(ValueError, match="Unknown OCR prediction"):
        load_evaluator().evaluate(cases, [*predictions, {"id": "unknown", "items": []}])

    missing_blank = [item for item in predictions if item["id"] != "blank-rest"]
    missing_metrics = load_evaluator().evaluate(cases, missing_blank)
    assert {failure["id"] for failure in missing_metrics["failures"]} >= {"blank-rest"}
