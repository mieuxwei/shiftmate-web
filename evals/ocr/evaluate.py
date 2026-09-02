"""Offline, deterministic metrics for versioned schedule-extraction outputs."""

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent


def evaluate(
    cases: list[dict[str, Any]], predictions: list[dict[str, Any]]
) -> dict[str, float]:
    by_id = {prediction["id"]: prediction["items"] for prediction in predictions}
    expected_items = 0
    predicted_items = 0
    date_matches = 0
    time_matches = 0
    review_true = 0
    review_found = 0
    schema_valid = 0
    schema_total = 0
    for case in cases:
        expected = case["expected"]
        predicted = by_id.get(case["id"], [])
        expected_items += len(expected)
        predicted_items += len(predicted)
        for wanted, actual in zip(expected, predicted, strict=False):
            date_matches += actual.get("work_date") == wanted.get("work_date")
            time_matches += (actual.get("start_time"), actual.get("end_time")) == (
                wanted.get("start_time"),
                wanted.get("end_time"),
            )
            if wanted.get("needs_review"):
                review_true += 1
                review_found += bool(actual.get("needs_review"))
        for actual in predicted:
            schema_total += 1
            schema_valid += (
                isinstance(actual, dict)
                and "work_date" in actual
                and "start_time" in actual
                and "end_time" in actual
                and isinstance(actual.get("needs_review"), bool)
            )
    denominator = max(expected_items, 1)
    return {
        "date_exact_match": date_matches / denominator,
        "time_exact_match": time_matches / denominator,
        "missing_shift_rate": max(expected_items - predicted_items, 0) / denominator,
        "extra_shift_rate": max(predicted_items - expected_items, 0) / denominator,
        "schema_valid_rate": schema_valid / max(schema_total, 1),
        "needs_review_recall": review_found / max(review_true, 1),
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
