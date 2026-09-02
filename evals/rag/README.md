# RAG evaluation fixtures

`cases.json` is a synthetic, versioned fixture for `rag_answer_v1`. It includes
answerable, unanswerable, conflicting-section, version-sensitive, and
prompt-injection-like cases. It contains no private policy documents.

`synthetic_predictions.json` is a deterministic offline baseline with a
representative conflicting-section retrieval/refusal failure. A captured
model/retriever output can replace it without changing the expected labels. The
default gate never makes a live model call.

Run:

```bash
python evals/rag/evaluate.py [predictions.json]
```

The report includes Recall@k, citation correctness, groundedness, refusal
accuracy, average latency, and total Gemini call count.

Use `python evals/run.py` from the repository root to rebuild the versioned M10
reports, or `python evals/run.py --check` to fail when they are stale.
