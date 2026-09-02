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
and a compact expected-to-predicted confusion map. Ambiguous questions may use
the bounded LLM classifier at runtime, but this milestone gate intentionally
requires every versioned fixture case to have a deterministic route.
