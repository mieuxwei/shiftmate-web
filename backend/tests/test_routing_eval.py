import importlib.util
import json
from pathlib import Path
from types import ModuleType


def load_evaluator() -> ModuleType:
    path = Path("evals/routing/evaluate.py")
    spec = importlib.util.spec_from_file_location("routing_evaluate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_routing_fixture_covers_all_routes_and_adversarial_boundaries() -> None:
    root = Path("evals/routing")
    cases = json.loads((root / "cases.json").read_text(encoding="utf-8"))
    intents = {case["expected_intent"] for case in cases}
    tags = {tag for case in cases for tag in case["tags"]}

    assert intents == {"schedule", "policy", "hybrid", "unsupported"}
    assert {"prompt-injection-like", "raw-sql", "write", "english"} <= tags
    metrics = load_evaluator().evaluate(cases)
    assert metrics["sample_count"] == 10
    assert metrics["accuracy"] == 1.0
    assert metrics["deterministic_coverage"] == 1.0
    assert metrics["fallback_count"] == 0
