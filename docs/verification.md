# Verification log

Record commands and observable results here at milestone gates. Do not record
secrets, tokens, private source data, or full model payloads.

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
