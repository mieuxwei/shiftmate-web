# M10 offline evaluation report

Generated from versioned synthetic fixtures by `python evals/run.py`.
No network, credential, database, paid platform, or live model is used.

## OCR

Samples: 9; failed cases: 3.

Metrics:

- `expected_item_count`: 9
- `predicted_item_count`: 8
- `date_exact_match`: 0.8888888888888888
- `time_exact_match`: 0.7777777777777778
- `missing_shift_rate`: 0.1111111111111111
- `extra_shift_rate`: 0.0
- `schema_valid_rate`: 1.0
- `needs_review_recall`: 0.8

Observed failures:

- `skewed`: {"id": "skewed", "reasons": ["time_mismatch"]}
- `multiple-dates`: {"id": "multiple-dates", "reasons": ["missing_shift"]}
- `illegible`: {"id": "illegible", "reasons": ["missed_review_flag"]}

Limitations:

- Synthetic structured outputs do not measure image decoding quality.
- Position-based item matching can penalize reordered shifts.
- Nine cases are directional evidence, not a production benchmark.

## RAG

Samples: 5; failed cases: 1.

Metrics:

- `recall_at_k`: 0.9
- `citation_correctness`: 1.0
- `groundedness`: 0.8
- `refusal_accuracy`: 0.8
- `average_latency_ms`: 73.0
- `gemini_call_count`: 9.0

Observed failures:

- `conflicting-overtime`: {"id": "conflicting-overtime", "reasons": ["retrieval_miss", "ungrounded_answer", "refusal_error"]}

Limitations:

- Synthetic chunks do not represent every PDF layout or language variant.
- Groundedness is a versioned human label, not an automated fact checker.
- Latency values are captured fixture data, not live provider performance.

## ROUTING

Samples: 12; failed cases: 2.

Metrics:

- `accuracy`: 0.8333333333333334
- `deterministic_coverage`: 0.8333333333333334
- `fallback_count`: 2
- `confusion`: {"hybrid->hybrid": 2, "policy->ambiguous": 1, "policy->policy": 2, "schedule->ambiguous": 1, "schedule->schedule": 3, "unsupported->unsupported": 3}

Observed failures:

- `terse-leave`: {"id": "terse-leave", "expected": "policy", "actual": "ambiguous"}
- `terse-week`: {"id": "terse-week", "expected": "schedule", "actual": "ambiguous"}

Limitations:

- Keyword routing is intentionally conservative and may defer terse queries.
- The fixture does not estimate accuracy of the optional Gemini fallback.
- Twelve synthetic questions are directional evidence, not traffic telemetry.

## Failure-mode coverage

- `gemini-unavailable-import` — Persist a bounded retryable failure code and create no candidate shifts. Test: `backend/tests/test_import_service.py::test_gemini_failure_is_persisted_with_safe_retryable_code`
- `supabase-jwks-unavailable` — Fail closed as an invalid bearer token without accepting an unverifiable identity. Test: `backend/tests/test_auth.py::test_supabase_jwks_unavailable_fails_closed`
- `calendar-api-unavailable` — Record a retryable sync failure while preserving confirmed shift truth. Test: `backend/tests/test_calendar_service.py::test_provider_failure_is_retryable_and_shift_truth_is_unchanged`

These are deterministic failure-injection tests. The report does not claim
availability or latency characteristics for Gemini, Supabase, or Google.
