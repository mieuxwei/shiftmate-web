"""Offline deterministic metrics for owner-scoped policy RAG predictions."""

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
        raise ValueError("Duplicate RAG case id")
    if len(prediction_ids) != len(set(prediction_ids)):
        raise ValueError("Duplicate RAG prediction id")
    unknown_ids = set(prediction_ids) - set(case_ids)
    if unknown_ids:
        raise ValueError(f"Unknown RAG prediction ids: {sorted(unknown_ids)}")
    by_id = {prediction["id"]: prediction for prediction in predictions}
    recall_total = 0.0
    citation_correct = 0
    grounded = 0
    refusal_correct = 0
    latency_total = 0.0
    calls_total = 0
    failures: list[dict[str, object]] = []
    for case in cases:
        prediction = by_id.get(case["id"], {})
        relevant = set(case["relevant_chunk_ids"])
        retrieved = set(prediction.get("retrieved_chunk_ids", []))
        citations = set(prediction.get("citation_chunk_ids", []))
        if relevant:
            recall = len(retrieved & relevant) / len(relevant)
        else:
            recall = float(not retrieved)
        recall_total += recall
        citations_ok = citations <= relevant and (
            bool(citations) == (not case["should_refuse"])
        )
        citation_correct += citations_ok
        is_grounded = bool(prediction.get("grounded"))
        grounded += is_grounded
        refusal_ok = prediction.get("refused") == case["should_refuse"]
        refusal_correct += refusal_ok
        latency_total += float(prediction.get("latency_ms", 0))
        calls_total += int(prediction.get("gemini_call_count", 0))
        reasons: list[str] = []
        if case["id"] not in by_id:
            reasons.append("missing_prediction")
        if recall < 1:
            reasons.append("retrieval_miss")
        if not citations_ok:
            reasons.append("citation_error")
        if not is_grounded:
            reasons.append("ungrounded_answer")
        if not refusal_ok:
            reasons.append("refusal_error")
        if reasons:
            failures.append({"id": case["id"], "reasons": reasons})
    count = max(len(cases), 1)
    return {
        "sample_count": len(cases),
        "recall_at_k": recall_total / count,
        "citation_correctness": citation_correct / count,
        "groundedness": grounded / count,
        "refusal_accuracy": refusal_correct / count,
        "average_latency_ms": latency_total / count,
        "gemini_call_count": float(calls_total),
        "failure_count": len(failures),
        "failures": failures,
        "limitations": [
            "Synthetic chunks do not represent every PDF layout or language variant.",
            "Groundedness is a versioned human label, not an automated fact checker.",
            "Latency values are captured fixture data, not live provider performance.",
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
