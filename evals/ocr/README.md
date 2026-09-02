# OCR evaluation fixtures

`cases.json` is the versioned, synthetic fixture manifest for
`schedule_extraction_v1`. It covers clear, shadowed, skewed, overnight,
blank/rest-day, multiple-person, multiple-date, marked, and illegible inputs.
No private schedule data is included.

`synthetic_predictions.json` is a deterministic reference output used to prove
the local metric runner. Replace it with captured, schema-validated model output
to evaluate a Gemini model without changing expected labels.

Run:

```bash
python evals/ocr/evaluate.py [predictions.json]
```

The report includes date/time exact match, missing/extra shift rates,
schema-valid rate, and `needs_review` recall. Live model calls are deliberately
not part of the default gate, so tests remain free, repeatable, and safe.
