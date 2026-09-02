# Verification log

Record commands and observable results here at milestone gates. Do not record
secrets, tokens, private source data, or full model payloads.

## 2026-09-02 — M6 LangGraph hybrid assistant milestone gate

- Added the real typed LangGraph workflow specified in the plan: normalize,
  deterministic-first route, schedule/policy/hybrid/unsupported nodes, evidence
  validation, answer composition, and END. The compiled graph has no
  checkpointer and tests prove one request cannot leak facts or citations into
  the next.
- Schedule facts and payroll estimates come from the existing owner-scoped
  deterministic analytics service. Policy evidence uses the existing
  LangChain/pgvector RLS retriever. Raw SQL and write requests are rejected
  before model routing; schedule-only requests still work with Gemini
  unconfigured.
- Hybrid consecutive-day evaluation refuses when shifts, citations, a supported
  rule threshold, or a single unambiguous threshold is missing. Supported
  results preserve deterministic facts and database-derived page citations for
  the bounded Gemini response prompt.
- Added the authenticated assistant API plus responsive conversation UI with
  route, tool status, schedule facts, citations, refusal state, and the explicit
  legal/HR/payroll portfolio disclaimer.
- `ruff format --check .`, `ruff check .`, and strict `mypy` passed. The full
  Python gate passed all 80 tests against disposable PostgreSQL 17 + pgvector,
  including all 15 integration tests, with 93% `backend.app` coverage.
- Frontend Prettier, ESLint, strict typecheck, and production build passed from
  an identical temporary copy; all 34 tests passed. The bundle contains 75
  modules, 441.70 kB JavaScript (125.14 kB gzip), and 13.64 kB CSS (3.26 kB
  gzip).
- The ten-case offline route report produced 1.0 accuracy, 1.0 deterministic
  coverage, zero fallbacks, and correct results for schedule (3), policy (2),
  hybrid (2), and unsupported (3) cases.
- `docker build --target runtime -t shiftmate-web:m6 .` passed from the
  identical temporary copy. The non-root `app` runtime served the production
  SPA, production health response, and typed `/api/v1/assistant/query` OpenAPI
  contract.
- No live Gemini request, private data, credential, paid service, or cloud
  resource was used. Docker and frontend temporary-copy verification was needed
  because of the already-recorded macOS file-provider/sandbox behavior.

M6 passed its complete acceptance gate and is `COMPLETE`. Commit and push remain
pending explicit user approval.

## 2026-09-02 — M5 LangChain RAG and citations

- Added migration `20260902_0004`: policy embeddings are `vector(768)`, cosine
  HNSW is indexed, `(owner_id, sha256)` is unique, and indexing failures use a
  bounded error code. Empty-database upgrade, downgrade/upgrade, catalog checks,
  and constraints passed on disposable PostgreSQL 17 plus pgvector.
- The LangChain `BaseRetriever` runs on the authenticated request connection,
  explicitly filters the current owner, and remains behind forced RLS. A real
  cross-owner vector query and the policy API integration returned only User A's
  synthetic chunk; User B's matching-vector injection text and document were
  invisible.
- Retrieval uses a no-op callback manager rather than environment-controlled
  tracing, preventing accidental export of questions or policy chunks.
- PDF validation, real text extraction, cleaning, overlapping per-page chunks,
  temporary-file cleanup, normalized Gemini document/query embeddings, score
  threshold refusal, grounded prompt boundaries, database-derived citations,
  deletion, and concurrent-safe SHA-256 deduplication are covered by tests.
- The UI lists/deletes documents, requires a synthetic/anonymous-data
  confirmation before upload, queries ready policies, renders page citations,
  and distinguishes explicit refusal from an answered question.
- Offline `python evals/rag/evaluate.py` covered answerable, unanswerable,
  conflicting, version-sensitive, and prompt-injection-like cases: Recall@k,
  citation correctness, groundedness, and refusal accuracy were all `1.0`;
  average synthetic latency was `73 ms` and total call count was `9`.
- Backend gate: Ruff format/lint and strict mypy passed. The isolated Docker test
  target ran all 71 unit/integration tests together against PostgreSQL and passed
  with 93% `backend.app` coverage; the separate host PostgreSQL gate also passed
  all 15 integration tests.
- Frontend gate: Prettier, ESLint, TypeScript, all 32 Vitest tests, and the Vite
  production build passed.
- `docker build -t shiftmate-web:m5 .` passed. A non-root (`app`) container served
  the production health endpoint, UI, and OpenAPI including
  `/api/v1/assistant/query`.
- The Dockerfile also exposes an isolated `test` target so the full backend gate
  can be rerun without macOS file-provider reads; the production `runtime` target
  remains non-root and excludes development dependencies.

M5 passed its complete milestone gate and is `COMPLETE`. No live Gemini request,
private document, credential, paid service, or cloud resource was used. The
changes remain uncommitted pending explicit user approval.

## 2026-09-02 — M0 repository boundary and Codex context

- `git remote -v`: fetch and push both target the independent
  `mieuxwei/shiftmate-web` GitHub repository.
- Repository inspection before implementation: only `projectplan.md` existed;
  the branch had no commits.
- File review: M0 contains planning, safety, configuration placeholders, and
  documentation only; no application or legacy project files are present.
- Secret scan: repository-wide credential-pattern scan returned no findings.
- Formatting: `git diff --check --no-index` passed for every M0 file.
- Git status: M0 files are ready for the initial commit; clean-worktree result is
  verified immediately after commit.

No runtime, paid service, external API, or cloud resource was created or used.

## 2026-09-02 — M1 full-stack and Docker foundation

- Backend format/lint/type gate: `ruff format --check .`, `ruff check .`, and
  strict `mypy` passed.
- Backend tests: 3 tests passed; coverage was 87% for `backend.app`.
- Frontend format/lint/type gate: Prettier check, ESLint, and TypeScript project
  build passed.
- Frontend tests: 2 Vitest component tests passed.
- Frontend production build: Vite completed successfully and emitted the
  production assets in `frontend/dist`.
- Frozen install: `pnpm install --frozen-lockfile --offline` passed.
- Local same-origin smoke: Uvicorn served `/api/v1/health` with HTTP 200 and the
  built `/` page with the `ShiftMate Web` title.
- Dependency check: `pnpm peers check` reported no peer dependency issues.
- Docker environment: Docker 29.7.2 and Compose v5.5.0 connected to a local
  Linux/aarch64 daemon.
- Production image: `docker build -t shiftmate-web:m1 .` passed. The resulting
  arm64 image was 59,872,199 bytes and configured to run as non-root user `app`.
- Container smoke: `/`, `/api/v1/health`, `/docs`, and `/openapi.json` returned
  successfully; an unknown `/api/v1/*` route returned 404 rather than the SPA.
- Compose production-like smoke: the built UI and API were served together on
  port 8000.
- Compose dev smoke: Vite served the UI on port 5173 and proxied the health API
  to FastAPI. pnpm store and `node_modules` use named volumes and did not write
  dependency caches into the workspace.
- Cleanup: temporary smoke containers, Compose network, and Compose volumes were
  removed after verification; the locally built images remain available.

M1 passed its milestone gate and is `COMPLETE`. No credentials, paid service,
external API, or cloud resource was used.

## 2026-09-02 — M2 slice 1 migration and owner isolation

- Built `shiftmate-web:m2`; the production image includes Alembic configuration
  and migrations, and the existing frontend production build still passed.
- Started a disposable local PostgreSQL 17 container with tmpfs storage; no
  external database or Supabase project was used.
- Backend format/lint/type gate passed in Python 3.12: the format check covered
  16 files, Ruff reported no issues, and strict mypy reported no issues.
- Backend tests: 5 passed with 87% `backend.app` coverage, including two
  PostgreSQL integration tests.
- Migration round trip: downgrade to base, upgrade to head, downgrade to base,
  and final upgrade to head all passed from the disposable database.
- Schema inspection confirmed `profiles`, `shifts`, required shift constraints,
  forced RLS, and the `(owner_id, work_date)` index.
- RLS test used two synthetic UUID owners and a non-owner database role. User A
  saw only User A rows; User B update/delete returned no rows; a forged User B
  insert was rejected; an own-row insert succeeded.

This is a verified M2 slice, not the M2 milestone gate. JWT validation, the
remaining tables, pgvector, repository interfaces, ADRs, and Supabase
compatibility remain. No credentials, paid service, or cloud resource was used.

## 2026-09-02 — M2 slice 2 complete schema and pgvector

- Replaced the disposable test database image with PostgreSQL 17 plus pgvector;
  the image pulled and ran successfully on the local arm64 Docker environment.
- Empty-database upgrade created all 13 application tables and both `pgcrypto`
  and `vector` extensions. A vector exact-distance query returned the expected
  result without an approximate-search index.
- Migration round trip from head to base and back to head passed. Downgrade
  removes application objects while intentionally preserving shared extensions.
- All 12 user-owned tables have forced RLS and exactly one owner policy. The
  internal `scheduled_job_runs` table has forced RLS with no authenticated-user
  policy or grant.
- Schema inspection confirmed required indexes, shift constraints, and both job
  idempotency constraints. Chat storage has no chain-of-thought column.
- A composite owner foreign key rejected a synthetic User B child pointing to a
  User A import. Runtime RLS tests also isolated pay-rate rows and hid the
  internal job table from the ordinary test role.
- Python 3.12 gate passed: 17 files passed Ruff formatting, Ruff lint passed,
  strict mypy passed, and all 5 tests passed with 87% `backend.app` coverage.
- The final `shiftmate-web:m2` production image rebuilt successfully with both
  migrations and the frontend production bundle.

This is a verified M2 slice, not the M2 milestone gate. JWT validation,
request-scoped database identity, repository interfaces, ADRs, and Supabase
compatibility remain. No credentials, paid service, or cloud resource was used.

## 2026-09-02 — M2 slice 3 auth and request identity

- Implemented asymmetric Supabase JWT verification through the project JWKS
  endpoint with issuer, audience, expiry, subject, and role validation.
- Synthetic RSA tokens verified locally. `service_role` and wrong-audience
  tokens were rejected without using a Supabase project or private key.
- Ordinary database dependencies reject bypass-role configuration and use a
  bounded SQLAlchemy pool with psycopg prepared statements disabled.
- A direct PostgreSQL integration test confirmed each request transaction uses
  `authenticated`, sets only the verified JWT subject, sees only that owner's
  repository rows, and clears both role and subject when returned to the pool.
- Added a shift repository protocol and PostgreSQL implementation that does not
  accept an owner override.
- Recorded the migration/runtime credential split, service-role prohibition,
  transaction-local identity, and pool sizing in ADR 0002.
- Python 3.12 gate passed: 23 files passed formatting, Ruff lint and strict mypy
  passed, and all 10 tests passed with 84% `backend.app` coverage.

This is a verified local M2 slice. The remaining milestone gate is live
Supabase Free compatibility testing, which requires explicit approval before
external project creation. No credentials, paid service, or cloud resource was
used.

## 2026-09-02 — M2 live Supabase Free compatibility

- Provisioned the `shiftmate-web` project in the `ShiftMate Portfolio`
  organization on Supabase Free in Northeast Asia (Tokyo), using nano compute.
  The project reported Healthy; no GitHub integration, paid add-on, or dedicated
  IPv4 option was enabled.
- The public Auth JWKS endpoint returned a P-256 ES256 verification key, which is
  compatible with the application's asymmetric JWT allowlist. No private key,
  access token, or database password was read into the repository or log.
- Applied the offline SQL generated by Alembic revisions `20260902_0001` and
  `20260902_0002` through Supabase SQL Editor. A follow-up catalog query confirmed
  revision `20260902_0002`, all 13 application tables, RLS and forced RLS on all
  13, 12 owner-isolation policies, the vector extension, and RLS on the Alembic
  metadata table.
- A transaction using two fixed synthetic UUID owners switched to the live
  `authenticated` role and set only User A's transaction-local subject. User A
  saw one own row, updated and deleted zero User B rows, and inserted one own
  row. The transaction was rolled back, and a cleanup query confirmed zero
  synthetic profile rows remained.
- Added the Alembic metadata-table RLS hardening to the source migration so a
  fresh deployment matches the live Supabase schema.
- After that change, 32 files passed Ruff formatting, Ruff lint passed, strict
  mypy passed, and the no-database unit gate passed with 7 tests and 80%
  `backend.app` coverage; 3 PostgreSQL integration tests were skipped because
  this rerun intentionally had no database URL. The earlier disposable-Postgres
  gate remains the integration-test evidence.
- With explicit approval, created one temporary synthetic login role and used
  the application's existing bounded SQLAlchemy engine and `user_connection`
  dependency through Supabase's shared transaction pooler on port 6543. Two
  synthetic subjects both ran as `authenticated`; the same client connection
  was reused, and after each request the login role was restored and the JWT
  subject was empty. Psycopg prepared statements remained disabled.
- The temporary login role was immediately dropped after the test. A catalog
  query returned zero matching roles, and the generated password was cleared
  from browser-control memory. It was never written to a file, repository,
  command line, or verification output.

M2 passed its milestone gate and is `COMPLETE`. The live project remains on the
Supabase Free plan, and no paid resource or add-on was enabled.

## 2026-09-02 — M2 final source gate

- Started a fresh disposable local PostgreSQL 17 plus pgvector database after
  the final migration hardening was present in the working tree.
- All 32 files passed Ruff formatting, Ruff lint passed, and strict mypy passed.
- All 10 tests passed with 84% `backend.app` coverage. The three PostgreSQL
  integration tests exercised empty-database upgrade, downgrade/upgrade,
  extensions, constraints, indexes, composite owner foreign keys, job
  idempotency, forced RLS, cross-owner isolation, repository access, and
  transaction-local identity cleanup.
- Rebuilt the final `shiftmate-web:m2` production image successfully. The
  disposable database container was stopped and automatically removed.

## 2026-09-02 — M3 slice 1 deterministic schedule domain

- Added a framework-independent schedule domain module; no API, database write,
  UI, Gemini, credential, or external service is involved in the calculation.
- Nine targeted tests passed for cross-midnight shifts, break deduction,
  profile-timezone date conversion, spring/fall DST elapsed time, inclusive
  effective-date boundaries, missing and overlapping rates, input validation,
  and half-up cent rounding.
- Full no-database backend regression gate passed in an isolated Python 3.12
  container: all 35 files passed Ruff formatting, Ruff lint passed, strict mypy
  passed, and 16 tests passed with 3 PostgreSQL tests skipped.
- `backend.app` coverage was 87%; the new schedule domain module was 100%
  covered.

This is a verified M3 slice, not the M3 milestone gate. CRUD, schedule views,
pay-rate management, aggregate analytics, dashboard UI, and synthetic demo data
remain. No paid resource was created or used.

## 2026-09-02 — M3 slice 2 schedule aggregation

- Added deterministic schedule aggregation for shift count, total paid
  duration/hours, estimated pay, sorted shift-type counts, and longest
  consecutive-workday runs.
- Multiple shifts on the same local work date count once toward consecutive
  days; empty schedules return a zero summary without requiring a pay rate.
- Twelve focused schedule-domain and analytics tests passed.
- Full no-database backend regression gate passed in an isolated Python 3.12
  container: all 37 files passed Ruff formatting, Ruff lint passed, strict mypy
  passed, and 19 tests passed with 3 PostgreSQL tests skipped.
- `backend.app` coverage was 89%; both schedule domain modules were 100%
  covered.

This is a verified M3 slice, not the M3 milestone gate. CRUD, schedule views,
pay-rate management, dashboard UI, and synthetic demo data remain. No paid
resource was created or used.

## 2026-09-02 — M3 slice 3 owner-scoped shift list/create API

- Added typed request/response schemas, application service operations, and
  `GET`/`POST /api/v1/shifts` routes for manual shift listing and creation.
- Shift creation derives `work_date` from the authenticated owner's profile
  timezone, reuses the deterministic domain validation, fixes source to
  `manual`, and neither accepts nor returns `owner_id`.
- Repository SQL relies on request-local identity and forced RLS rather than an
  application-supplied owner filter; optional date bounds were verified both
  with and without query parameters.
- PostgreSQL API integration tests created two synthetic owners and confirmed
  only the authenticated owner's row was returned and the new row stored the
  authenticated owner ID. Invalid date ranges and naive timestamps returned
  HTTP 422.
- Full Python 3.12 backend gate passed against a disposable local PostgreSQL 17
  plus pgvector database: all 43 files passed Ruff formatting, Ruff lint and
  strict mypy passed, and all 27 tests passed with 94% `backend.app` coverage.
- The temporary database used tmpfs storage and was stopped and automatically
  removed after verification.

This is a verified M3 slice, not the M3 milestone gate. PATCH/DELETE, pay-rate
management, schedule/dashboard UI, and synthetic demo data remain. No paid
resource or external API was used.

## 2026-09-02 — M3 slice 4 complete manual shift CRUD

- Added owner-scoped `PATCH /api/v1/shifts/{shift_id}` and
  `DELETE /api/v1/shifts/{shift_id}` operations across repository, service,
  schemas, and API layers.
- Partial updates merge with the current RLS-visible row and then re-run full
  timestamp, break, timezone, and shift-type validation. Changing timestamps
  recalculates the local `work_date`.
- PATCH distinguishes an omitted note from `notes: null`, allowing notes to be
  explicitly cleared while rejecting empty patches and null required fields.
- PostgreSQL integration tests confirmed another owner's UUID cannot be updated
  or deleted and returns the same HTTP 404 as a missing row. Successful delete
  returns HTTP 204 with an empty body and repeated deletion returns 404.
- Full Python 3.12 backend gate passed against a disposable local PostgreSQL 17
  plus pgvector database: all 43 files passed Ruff formatting, Ruff lint and
  strict mypy passed, and all 31 tests passed with 95% `backend.app` coverage.
- The repository and schema modules were fully covered; service and shift API
  coverage were 97% and 98%. The tmpfs database was stopped and automatically
  removed after verification.

This is a verified M3 slice, not the M3 milestone gate. Pay-rate management,
schedule/dashboard UI, and synthetic demo data remain. No paid resource or
external API was used.

## 2026-09-02 — M3 slice 5 owner-scoped pay-rate list/create API

- Added typed repository, service, schema, and API layers for
  `GET /api/v1/pay-rates` and `POST /api/v1/pay-rates`.
- Effective periods are inclusive at both ends. Adjacent periods beginning the
  day after an existing end are accepted; shared boundary dates and all other
  overlaps return HTTP 409.
- Creation validates positive two-decimal rates and date ordering through
  Pydantic and the deterministic pay-rate domain object.
- Same-owner create operations take a transaction-scoped advisory lock before
  checking overlap, preventing concurrent application requests from both
  passing an empty overlap check. Owner identity comes only from request-local
  database state and is never accepted or returned by the API.
- PostgreSQL integration tests seeded another owner with an open-ended rate and
  confirmed it was invisible and did not affect the authenticated owner's list
  or overlap decision.
- Full Python 3.12 backend gate passed against a disposable local PostgreSQL 17
  plus pgvector database: all 48 files passed Ruff formatting, Ruff lint and
  strict mypy passed, and all 36 tests passed with 95% `backend.app` coverage.
  The new pay-rate repository, service, and schemas were fully covered.
- The tmpfs database was stopped and automatically removed after verification.

This is a verified M3 slice, not the M3 milestone gate. Pay-rate PATCH/DELETE,
schedule/dashboard UI, and synthetic demo data remain. No paid resource or
external API was used.

## 2026-09-02 — M3 slice 6 complete pay-rate management

- Added owner-scoped `PATCH /api/v1/pay-rates/{pay_rate_id}` and
  `DELETE /api/v1/pay-rates/{pay_rate_id}` across repository, service, schema,
  and API layers.
- Partial updates serialize on the same owner-specific transaction advisory
  lock as creates, exclude the edited record from overlap checks, and re-run
  deterministic rate/date validation.
- Repricing an existing period is allowed. Shrinking or moving a period is
  rejected with HTTP 409 when it would exclude a shift currently covered by
  that rate; deleting any rate that covers an existing shift is also rejected.
- PostgreSQL integration tests confirmed overlap rejection, successful
  repricing, in-use protection, empty/null PATCH validation, HTTP 204 delete,
  repeat-delete 404, and identical 404 behavior for another owner's rate.
- Full Python 3.12 backend gate passed against a disposable local PostgreSQL 17
  plus pgvector database: all 48 files passed Ruff formatting, Ruff lint and
  strict mypy passed, and all 40 tests passed with 95% `backend.app` coverage.
  Both repositories and both PATCH schemas were fully covered.
- The tmpfs database was stopped and automatically removed after verification.

This is a verified M3 slice, not the M3 milestone gate. The analytics API,
schedule/dashboard UI, and synthetic demo data remain. No paid resource or
external API was used.

## 2026-09-02 — M3 slice 7 owner-scoped analytics summary API

- Added `GET /api/v1/analytics/summary` with required inclusive `date_from` and
  `date_to` parameters and a maximum inclusive range of 366 days.
- Added a profile preferences repository for owner-visible timezone and
  currency. The analytics service loads RLS-filtered shifts and pay rates, then
  delegates all hours, pay, shift-type, and consecutive-day calculations to the
  existing deterministic domain function.
- The service rejects stored `work_date` values that do not match the shift
  start in the profile timezone. Missing/overlapping rates and inconsistent
  stored schedule data return HTTP 409 rather than partial or invented totals.
- PostgreSQL integration tests created two shifts at TWD 200/hour and confirmed
  the API returned exactly 14.5 paid hours, TWD 2900.00, two shift types, and a
  two-day run. Another owner's shift and open-ended rate were excluded by RLS.
- Invalid/reversed ranges returned HTTP 422 and a shift without a covering rate
  returned HTTP 409.
- Full Python 3.12 backend gate passed against a disposable local PostgreSQL 17
  plus pgvector database: all 53 files passed Ruff formatting, Ruff lint and
  strict mypy passed, and all 45 tests passed with 96% `backend.app` coverage.
  The analytics service and response schema were fully covered.
- The tmpfs database was stopped and automatically removed after verification.

This is a verified M3 slice, not the M3 milestone gate. Authenticated frontend
session/client work, schedule/dashboard UI, and synthetic demo data remain. No
paid resource or external API was used.

## 2026-09-02 — M3 slice 8 authenticated frontend session and API client

- Added the official Supabase JavaScript client behind a small injectable
  session gateway. Initial session lookup and auth-state subscription expose
  explicit unconfigured, loading, signed-out, and signed-in UI states without
  copying tokens into logs or project files.
- Added email/password sign-in and sign-out controls. Browser configuration uses
  only `VITE_SUPABASE_URL` and the public `VITE_SUPABASE_ANON_KEY`; the example
  environment file explicitly prohibits a service-role key in browser values.
- Added a typed API client for shift CRUD, pay-rate CRUD, and analytics summary.
  Every user-data request reads the current access token, attaches it as a bearer
  token, and fails locally when no authenticated session is available.
- Added component tests with a synthetic fake session and API-client tests for
  bearer headers, date filters, typed analytics responses, missing-session
  rejection, and API error details. No live account or user data was used.
- Frontend lint and strict TypeScript checks passed. Both test files passed with
  all 8 tests, and the production bundle built successfully (62 modules,
  404.77 kB JavaScript / 115.70 kB gzip).
- Docker Desktop could not consistently read macOS compressed/file-provider
  metadata on the repository's `index.html`. The identical tracked frontend
  contents and lockfile were copied to a local temporary directory for the final
  Prettier check and production build; both passed there. Lint, typecheck, and
  tests passed directly against the working tree.

This is a verified M3 slice, not the M3 milestone gate. Read-only schedule and
dashboard presentation, mutation UI, and synthetic demo data remain. No paid
resource or external API was used.

## 2026-09-02 — M3 slices 9–12 schedule/dashboard vertical slice

- Extended the deterministic analytics domain and API with profile timezone and
  Monday-based weekly paid-hour totals. The React dashboard only visualizes
  backend-returned hours and pay; it does not recalculate payroll.
- Added responsive month/week schedule views, date navigation, summary metrics,
  shift-type distribution, weekly-hour trend, consecutive-day display, loading,
  empty, and safe error states.
- Added authenticated shift create/update/two-step-delete controls. Local
  date-time fields convert through the profile timezone, including DST gap
  rejection, before sending UTC timestamps to the API.
- Added independently loaded effective-dated pay-rate create/update/two-step-delete
  controls so users can repair missing-rate analytics errors. Conflict and
  protected-deletion failures do not expose internal database details.
- Added `frontend/src/demo/m3-demo.json`, a credential-free read-only synthetic
  dataset with six shifts and one rate. A Python test proves its 40 paid hours,
  TWD 8,000.00 estimate, shift distribution, weekly trend, and two-day maximum
  consecutive run match the production domain calculator.
- Frontend component/unit coverage now includes API auth behavior, session UI,
  range navigation, timezone/DST conversion, dashboard states, shift CRUD,
  pay-rate CRUD, and the offline demo: 26 tests passed across 7 files.

## 2026-09-02 — M3 milestone gate

- `ruff format --check .`: 54 files already formatted.
- `ruff check .`: passed.
- `mypy`: strict checks passed for 29 source files.
- `pytest --cov=backend.app --cov-report=term-missing`: all 46 unit/integration
  tests passed against disposable PostgreSQL 17 + pgvector with 96% coverage;
  both domain modules and the analytics service retained 100% coverage.
- `pnpm --dir frontend format`, `lint`, `typecheck`, and `test`: passed; 26/26
  tests passed.
- `pnpm --dir frontend build`: passed; 72 modules, 427.40 kB JavaScript
  (121.24 kB gzip), and 9.14 kB CSS (2.48 kB gzip).
- `docker build -t shiftmate-web:m3 .`: passed from the identical clean local
  copy. The non-root production container served the SPA and returned
  `{"status":"ok","environment":"production"}` from `/api/v1/health`.
- In-app browser QA passed on the production container: credential-free demo
  launch, deterministic month summary, month-to-week transition (14.5 hours /
  TWD 2,900.00 for 2026-08-31–2026-09-06), and responsive 390 px layout.
- Docker Desktop's file-provider EIO required the clean temporary copy for
  reliable format/build reads. Source behavior was also checked directly in the
  working tree. The temporary app and tmpfs database containers were removed.

M3 acceptance passed: manual CRUD is owner-isolated, timezone/break/cross-day/
effective-rate tests pass, dashboard facts match the deterministic service, and
the complete milestone works without Gemini. No paid resource or external model
was used. M3 is complete and approved for commit/push.

## 2026-09-02 — M4 Gemini schedule import ETL milestone gate

- Added strict upload validation for extension, MIME, magic bytes, the 5 MB
  limit, valid PDFs, and the 40-page PDF limit. Tests verify generated server
  filenames, SHA-256 metadata, cleanup on success and every rejection path.
- Added the `gemini-2.5-flash` REST adapter, `schedule_extraction_v1` prompt, and
  strict structured schema. Adapter tests inspect the JSON response schema and
  safe quota mapping; no live key or model call was used.
- Added the owner-isolated persistent import workflow. Draft state is committed
  before the external call; candidates are normalized in the profile timezone,
  missing/invalid/DST-ambiguous times cannot be confirmed, and only explicitly
  confirmed valid candidates become `source='import'` shifts.
- Alembic `20260902_0003` adds deterministic item ordering and a unique committed
  shift link. PostgreSQL integration tests cover clean downgrade/upgrade, RLS,
  unconfirmed and invalid rows, and repeated idempotent commit: 14/14 passed.
- Added authenticated multipart API methods and responsive React source preview,
  item editor, warning/confirmation controls, commit state, and bounded
  quota/unavailable messages. Frontend format, lint, strict typecheck, 29/29
  tests, and production build passed (73 modules; 434.27 kB JS / 123.12 kB gzip).
- Python format, Ruff, and strict mypy passed for 38 source files. All 60 backend
  tests passed together against disposable PostgreSQL with 94% aggregate
  application coverage.
- The nine-family offline OCR fixture gate reported 1.0 for date exact match,
  time exact match, schema-valid rate, and `needs_review` recall, with 0.0
  missing and extra shift rates.
- `docker build -t shiftmate-web:m4 .` passed. The non-root production container
  served the SPA, production health response, and all four import OpenAPI paths.
- Secret-pattern and application logging inspections found no credential,
  original upload, or raw model-content logging. Only synthetic fixtures were
  used; no paid resource was created or called.

M4 acceptance passed: unconfirmed items never enter `shifts`, invalid/ambiguous
times fail closed, repeated commit is idempotent, Gemini failure states are safe
and retryable by re-upload, and temporary/raw content is not logged. M4 is
complete and was approved for commit/push.
