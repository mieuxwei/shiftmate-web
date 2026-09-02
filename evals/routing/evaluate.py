"""Offline deterministic metrics for the M6 intent router."""

import json
from collections import Counter
from pathlib import Path
from typing import Any

from backend.app.services.assistant import deterministic_route

ROOT = Path(__file__).parent


def evaluate(cases: list[dict[str, Any]]) -> dict[str, object]:
    correct = 0
    fallback_count = 0
    confusion: Counter[str] = Counter()
    for case in cases:
        predicted = deterministic_route(case["question"])
        if predicted is None:
            fallback_count += 1
            label = "ambiguous"
        else:
            label = predicted
        expected = str(case["expected_intent"])
        correct += label == expected
        confusion[f"{expected}->{label}"] += 1
    count = len(cases)
    return {
        "sample_count": count,
        "accuracy": correct / count if count else 0.0,
        "deterministic_coverage": (count - fallback_count) / count if count else 0.0,
        "fallback_count": fallback_count,
        "confusion": dict(sorted(confusion.items())),
    }


def main() -> None:
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    print(json.dumps(evaluate(cases), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
