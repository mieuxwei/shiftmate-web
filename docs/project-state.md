# Project state

Last updated: 2026-09-02

## Current position

- Last completed milestone: **M2 — PostgreSQL, Auth and RLS**
- Active milestone: none; **M3 — Schedule domain and Dashboard** is next
- Blockers: none

## Completed

- Confirmed this is the independent `shiftmate-web` GitHub repository.
- Added repository safety rules, ignore rules, environment placeholders, license,
  and a README skeleton.
- Added persistent project state, verification log, task template, initial ADR,
  and synthetic-data policy.
- Confirmed no earlier project files, runtime dependencies, secrets, or private
  sample data are present.
- Added a React/TypeScript/Vite demo shell that reports live FastAPI health.
- Added typed FastAPI settings, OpenAPI, health routing, tests, and static SPA
  serving for the production bundle.
- Added the multi-stage production image, Compose workflows, pinned frontend
  lockfile, Python and TypeScript quality gates, and GitHub Actions validation.
- Verified the production image serves the React UI, health API, OpenAPI, and
  docs as a non-root user on local Docker.
- Verified both the production-like Compose service and the dev Vite-to-FastAPI
  proxy workflow; pnpm dependencies use isolated named volumes.

## Latest milestone

- M2 slice 1 is complete: Alembic can rebuild `profiles` and `shifts`; PostgreSQL
  integration tests cover downgrade/upgrade, constraints, the owner/date index,
  and two-user RLS isolation.
- M2 slice 2 is complete: the remaining planned tables, pgvector, composite
  owner foreign keys, indexes, constraints, and forced RLS policies rebuild from
  an empty PostgreSQL database.
- M2 slice 3 is complete: asymmetric JWKS JWT validation, request-local database
  role/identity handling, a shift repository interface, bounded pooling, and the
  service-role/pooling ADR have local tests.
- Live Supabase Free compatibility is complete: the Tokyo project is healthy,
  its ES256 JWKS is compatible, both Alembic revisions applied, all 13
  application tables and pgvector were verified, a rolled-back two-user
  transaction passed owner isolation, and the application connection path
  passed through the transaction pooler with clean role/subject reset.

## Next task packet

Start the smallest M3 vertical slice: deterministic schedule-domain calculations
for cross-midnight shifts, breaks, timezone handling, and effective-dated pay
rates, with targeted unit tests. Keep Gemini and UI work out of that first slice.

## Known risks

- Free-tier limits and provider policies can change; verify official policies
  again before provisioning in later milestones.
- Docker Desktop's CLI directory was not automatically present in this shell's
  PATH; the README documents the macOS PATH fallback.
- The Supabase project now contains the M2 schema. Future migration changes must
  preserve compatibility between Alembic's direct migration path and the
  transaction-pooled runtime path.
