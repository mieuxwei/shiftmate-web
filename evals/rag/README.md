# RAG evaluation fixtures

`cases.json` is a synthetic, versioned fixture for `rag_answer_v1`. It includes
answerable, unanswerable, conflicting-section, version-sensitive, and
prompt-injection-like cases. It contains no private policy documents.

`synthetic_predictions.json` proves the deterministic local metric runner. A
captured model/retriever output can replace it without changing the expected
labels. The default gate never makes a live model call.

Run:

```bash
python evals/rag/evaluate.py [predictions.json]
```

The report includes Recall@k, citation correctness, groundedness, refusal
accuracy, average latency, and total Gemini call count.
