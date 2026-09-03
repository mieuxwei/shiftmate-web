# Routing evaluation fixture

`cases.json` contains only synthetic questions and covers schedule, policy,
hybrid, unsupported, English/Traditional Chinese, write requests, raw SQL, and
prompt-injection-like input. The runner imports the production deterministic
router and never calls Gemini or a paid service.

Run:

```bash
python evals/routing/evaluate.py
```

The report shows sample count, accuracy, deterministic coverage, fallback count,
a compact expected-to-predicted confusion map, and case-level failures. Two
terse questions intentionally expose the deterministic router's fallback
boundary. Ambiguous questions may use the bounded LLM classifier at runtime,
but the offline report does not claim fallback-model accuracy.

Use `python evals/run.py` from the repository root to rebuild the versioned
reports, or `python evals/run.py --check` to fail when they are stale.
