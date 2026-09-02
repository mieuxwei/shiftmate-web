# Failure-mode evaluation

`cases.json` maps each required unavailable-dependency scenario to its bounded
expected behavior and deterministic pytest node. The tests inject failures into
the production authentication, import, and Calendar service boundaries; they do
not call Gemini, Supabase, Google, or any paid platform.

Run the complete M10 evaluation gate from the repository root:

```bash
python evals/run.py --check
pytest \
  backend/tests/test_ocr_eval.py \
  backend/tests/test_rag_eval.py \
  backend/tests/test_routing_eval.py \
  backend/tests/test_auth.py::test_supabase_jwks_unavailable_fails_closed \
  backend/tests/test_import_service.py::test_gemini_failure_is_persisted_with_safe_retryable_code \
  backend/tests/test_calendar_service.py::test_provider_failure_is_retryable_and_shift_truth_is_unchanged
```

Run `python evals/run.py` after an intentional fixture or metric change to
rebuild the versioned JSON reports and `reports/summary.md`, then review the
diff. A stale report makes `--check` fail.
