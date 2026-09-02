# OCR evaluation fixtures

`cases.json` is the versioned, synthetic fixture manifest for
`schedule_extraction_v1`. It covers clear, shadowed, skewed, overnight,
blank/rest-day, multiple-person, multiple-date, marked, and illegible inputs.
No private schedule data is included.

`synthetic_predictions.json` is a deterministic offline baseline with three
intentional representative misses. It proves that the report exposes errors
instead of selecting only successful examples. Replace it with captured,
schema-validated model output to evaluate a Gemini model without changing
expected labels.

Run:

```bash
python evals/ocr/evaluate.py [predictions.json]
```

The report includes date/time exact match, missing/extra shift rates,
schema-valid rate, and `needs_review` recall. Live model calls are deliberately
not part of the default gate, so tests remain free, repeatable, and safe.

Use `python evals/run.py` from the repository root to rebuild the versioned M10
reports, or `python evals/run.py --check` to fail when they are stale.
