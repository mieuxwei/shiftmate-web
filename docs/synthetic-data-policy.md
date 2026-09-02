# Synthetic data policy

ShiftMate Web is a portfolio and demonstration project. Repository fixtures,
screenshots, prompts, evaluations, and live demonstrations must use synthetic or
irreversibly anonymized data.

## Allowed

- Invented people, employers, schedules, rates, policies, and identifiers.
- Generated schedule images and PDFs that contain no source personal data.
- Clearly fictional policy documents written for evaluation.
- Anonymized examples only when re-identification is not reasonably possible.

## Prohibited

- Real employee schedules, payroll, employment records, or company documents.
- Names, email addresses, phone numbers, employee IDs, account IDs, or internal
  URLs copied from a real workplace or earlier project.
- Production credentials, OAuth tokens, private keys, or real API payloads.
- Uploading private or confidential material to Gemini Free Tier.

## Fixture conventions

- Use obviously fictional names and organizations.
- Use non-sensitive example domains and placeholder IDs.
- Label samples and screenshots as synthetic where practical.
- Review generated fixtures before commit for accidental personal information.
- Keep raw uploaded files out of Git unless they are deliberate synthetic test
  fixtures and are small enough for repository use.

If the origin or safety of data is uncertain, do not use it. Replace it with a
new synthetic fixture and record any lasting policy decision in an ADR.
