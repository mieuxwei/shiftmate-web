# ShiftMate Web agent instructions

Read `docs/project-state.md` first, then read only the current milestone's
sections and relevant files. `projectplan.md` is the source of truth.

## Non-negotiable rules

- Work on at most one active milestone. Use the smallest verifiable slices as
  internal implementation checkpoints, but do not stop or hand off merely
  because a slice is complete.
- Once a milestone starts, continue through its remaining slices until either
  the complete milestone gate passes or progress requires a user decision,
  approval, credential, external action, or other input that cannot be safely
  inferred. A failed check is not a stopping point while an in-scope fix or
  diagnostic path remains.
- Do not copy, modify, import, or depend on `line-bot-calendar`.
- Preserve user changes; never use destructive Git operations.
- Use only synthetic or anonymized data. Never send private schedules, payroll,
  or internal documents to Gemini Free Tier.
- Never commit secrets. Use environment variables and platform secret stores.
- Keep expected cloud cost at NT$0. Stop for approval before any potentially
  paid resource, plan, model, add-on, or configuration.
- LLMs must not calculate payroll, execute SQL, or write confirmed shifts.
- User-owned data must be owner-isolated; ordinary requests must not bypass RLS
  with a service-role key.
- Update the plan or an ADR before intentionally deviating from architecture.
- Record milestone verification in `docs/verification.md`.

## Working pattern

1. Inspect Git status and the files relevant to the active milestone.
2. Use the task packet in `docs/codex-task-template.md`.
3. Prefer targeted formatter, type checks, and tests during implementation,
   then continue directly to the next slice in the same milestone.
4. Run the milestone gate before marking it complete. Intermediate slice
   verification is a checkpoint, not a handoff boundary.
5. Stop only when user input is required or the complete milestone gate has
   passed. At either stopping point, report changed files, verification, risks,
   and the exact decision or next milestone.
6. Do not commit or push a completed milestone until the user explicitly
   approves that milestone's commit/push. Once approved, commit all verified
   milestone changes and push the current branch to its configured upstream
   without asking again. Never rewrite remote history; if push fails, diagnose
   and use only safe, non-destructive recovery.

## Verification commands

M0:

```bash
git status --short --branch
git ls-files
git grep -nEi '(api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|password)[[:space:]]*[:=][[:space:]]*[^[:space:]$<{]+'
```

M1:

```bash
ruff format --check .
ruff check .
mypy
pytest --cov=backend.app --cov-report=term-missing
pnpm --dir frontend format
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
docker build -t shiftmate-web:m1 .
docker run --rm -p 8080:8080 shiftmate-web:m1
```

M4 adds this feature gate before the full M1-quality gate:

```bash
M2_TEST_DATABASE_URL=postgresql+psycopg://postgres:shiftmate_local_only@localhost:5432/shiftmate_test pytest -m integration
python evals/ocr/evaluate.py
```
