import importlib.util
import json
from pathlib import Path
from types import ModuleType


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
    assert metrics == {
        "recall_at_k": 1.0,
        "citation_correctness": 1.0,
        "groundedness": 1.0,
        "refusal_accuracy": 1.0,
        "average_latency_ms": 73.0,
        "gemini_call_count": 9.0,
    }
