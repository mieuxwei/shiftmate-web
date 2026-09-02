"""Offline deterministic metrics for the M6 intent router."""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
PROJECT_ROOT = ROOT.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.assistant import deterministic_route  # noqa: E402


def evaluate(cases: list[dict[str, Any]]) -> dict[str, object]:
    case_ids = [case["id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Duplicate routing case id")
    correct = 0
    fallback_count = 0
    confusion: Counter[str] = Counter()
    failures: list[dict[str, str]] = []
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
        if label != expected:
            failures.append(
                {"id": str(case["id"]), "expected": expected, "actual": label}
            )
    count = len(cases)
    return {
        "sample_count": count,
        "accuracy": correct / count if count else 0.0,
        "deterministic_coverage": (count - fallback_count) / count if count else 0.0,
        "fallback_count": fallback_count,
        "confusion": dict(sorted(confusion.items())),
        "failure_count": len(failures),
        "failures": failures,
        "limitations": [
            "Keyword routing is intentionally conservative and may defer "
            "terse queries.",
            "The fixture does not estimate accuracy of the optional Gemini fallback.",
            "Twelve synthetic questions are directional evidence, not traffic "
            "telemetry.",
        ],
    }


def main() -> None:
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    print(json.dumps(evaluate(cases), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
