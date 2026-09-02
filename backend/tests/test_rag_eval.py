import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


def load_evaluator() -> ModuleType:
    path = Path("evals/rag/evaluate.py")
    spec = importlib.util.spec_from_file_location("rag_evaluate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_synthetic_rag_fixture_covers_required_cases_and_metrics() -> None:
    root = Path("evals/rag")
    cases = json.loads((root / "cases.json").read_text(encoding="utf-8"))
    predictions = json.loads(
        (root / "synthetic_predictions.json").read_text(encoding="utf-8")
    )
    tags = {tag for case in cases for tag in case["tags"]}
    assert {
        "answerable",
        "unanswerable",
        "conflicting-sections",
        "version-sensitive",
        "prompt-injection-like",
    } <= tags

    metrics = load_evaluator().evaluate(cases, predictions)
    assert metrics["sample_count"] == 5
    assert metrics["recall_at_k"] == 0.9
    assert metrics["citation_correctness"] == 1.0
    assert metrics["groundedness"] == 0.8
    assert metrics["refusal_accuracy"] == 0.8
    assert metrics["average_latency_ms"] == 73.0
    assert metrics["gemini_call_count"] == 9.0
    assert metrics["failure_count"] == 1
    assert {failure["id"] for failure in metrics["failures"]} == {
        "conflicting-overtime",
    }

    with pytest.raises(ValueError, match="Duplicate RAG prediction"):
        load_evaluator().evaluate(cases, [*predictions, predictions[0]])
