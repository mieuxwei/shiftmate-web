"""Offline, deterministic metrics for versioned schedule-extraction outputs."""

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent


def evaluate(
    cases: list[dict[str, Any]], predictions: list[dict[str, Any]]
) -> dict[str, object]:
    case_ids = [case["id"] for case in cases]
    prediction_ids = [prediction["id"] for prediction in predictions]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Duplicate OCR case id")
    if len(prediction_ids) != len(set(prediction_ids)):
        raise ValueError("Duplicate OCR prediction id")
    unknown_ids = set(prediction_ids) - set(case_ids)
    if unknown_ids:
        raise ValueError(f"Unknown OCR prediction ids: {sorted(unknown_ids)}")
    by_id = {prediction["id"]: prediction["items"] for prediction in predictions}
    expected_items = 0
    predicted_items = 0
    date_matches = 0
    time_matches = 0
    review_true = 0
    review_found = 0
    schema_valid = 0
    schema_total = 0
    failures: list[dict[str, object]] = []
    for case in cases:
        expected = case["expected"]
        predicted = by_id.get(case["id"], [])
        reasons: list[str] = []
        if case["id"] not in by_id:
            reasons.append("missing_prediction")
        expected_items += len(expected)
        predicted_items += len(predicted)
        for wanted, actual in zip(expected, predicted, strict=False):
            date_match = actual.get("work_date") == wanted.get("work_date")
            time_match = (
                actual.get("start_time"),
                actual.get("end_time"),
            ) == (
                wanted.get("start_time"),
                wanted.get("end_time"),
            )
            date_matches += date_match
            time_matches += time_match
            if not date_match and "date_mismatch" not in reasons:
                reasons.append("date_mismatch")
            if not time_match and "time_mismatch" not in reasons:
                reasons.append("time_mismatch")
            if wanted.get("needs_review"):
                review_true += 1
                review_match = bool(actual.get("needs_review"))
                review_found += review_match
                if not review_match and "missed_review_flag" not in reasons:
                    reasons.append("missed_review_flag")
        for actual in predicted:
            schema_total += 1
            schema_valid += (
                isinstance(actual, dict)
                and "work_date" in actual
                and "start_time" in actual
                and "end_time" in actual
                and isinstance(actual.get("needs_review"), bool)
            )
        if len(predicted) < len(expected):
            reasons.append("missing_shift")
        elif len(predicted) > len(expected):
            reasons.append("extra_shift")
        if reasons:
            failures.append({"id": case["id"], "reasons": reasons})
    denominator = max(expected_items, 1)
    return {
        "sample_count": len(cases),
        "expected_item_count": expected_items,
        "predicted_item_count": predicted_items,
        "date_exact_match": date_matches / denominator,
        "time_exact_match": time_matches / denominator,
        "missing_shift_rate": max(expected_items - predicted_items, 0) / denominator,
        "extra_shift_rate": max(predicted_items - expected_items, 0) / denominator,
        "schema_valid_rate": schema_valid / max(schema_total, 1),
        "needs_review_recall": review_found / max(review_true, 1),
        "failure_count": len(failures),
        "failures": failures,
        "limitations": [
            "Synthetic structured outputs do not measure image decoding quality.",
            "Position-based item matching can penalize reordered shifts.",
            "Nine cases are directional evidence, not a production benchmark.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "predictions", nargs="?", type=Path, default=ROOT / "synthetic_predictions.json"
    )
    args = parser.parse_args()
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    print(json.dumps(evaluate(cases, predictions), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
