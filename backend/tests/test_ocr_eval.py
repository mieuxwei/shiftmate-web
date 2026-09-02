import importlib.util
import json
from pathlib import Path
from types import ModuleType


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
    assert metrics == {
        "date_exact_match": 1.0,
        "time_exact_match": 1.0,
        "missing_shift_rate": 0.0,
        "extra_shift_rate": 0.0,
        "schema_valid_rate": 1.0,
        "needs_review_recall": 1.0,
    }
