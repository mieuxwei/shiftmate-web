"""Offline deterministic metrics for owner-scoped policy RAG predictions."""

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent


def evaluate(
    cases: list[dict[str, Any]], predictions: list[dict[str, Any]]
) -> dict[str, float]:
    by_id = {prediction["id"]: prediction for prediction in predictions}
    recall_total = 0.0
    citation_correct = 0
    grounded = 0
    refusal_correct = 0
    latency_total = 0.0
    calls_total = 0
    for case in cases:
        prediction = by_id.get(case["id"], {})
        relevant = set(case["relevant_chunk_ids"])
        retrieved = set(prediction.get("retrieved_chunk_ids", []))
        citations = set(prediction.get("citation_chunk_ids", []))
        if relevant:
            recall_total += len(retrieved & relevant) / len(relevant)
        else:
            recall_total += float(not retrieved)
        citation_correct += citations <= relevant and (
            bool(citations) == (not case["should_refuse"])
        )
        grounded += bool(prediction.get("grounded"))
        refusal_correct += prediction.get("refused") == case["should_refuse"]
        latency_total += float(prediction.get("latency_ms", 0))
        calls_total += int(prediction.get("gemini_call_count", 0))
    count = max(len(cases), 1)
    return {
        "recall_at_k": recall_total / count,
        "citation_correctness": citation_correct / count,
        "groundedness": grounded / count,
        "refusal_accuracy": refusal_correct / count,
        "average_latency_ms": latency_total / count,
        "gemini_call_count": float(calls_total),
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
