# Project state

Last updated: 2026-09-02

## Current position

- Last completed milestone: **M3 — Schedule domain and Dashboard**
- Active milestone: **None; M4 not started**
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

- M3 is complete: authenticated users can manage owner-isolated shifts and
  effective-dated pay rates, switch between month/week schedules, and view
  deterministic hours, pay, shift-type, weekly-trend, and consecutive-day facts.
  A credential-free read-only demo uses one verified synthetic fixture.
- M3 slices 9–12 are complete: the responsive workspace covers loading, empty,
  and safe error states; manual shift and pay-rate CRUD; timezone-aware local
  input conversion; dashboard charts; and the offline synthetic demo.
- M3 slice 8 is complete: the browser now exposes explicit unconfigured,
  signed-out, loading, and signed-in states through a testable Supabase session
  gateway. A typed API client attaches the current bearer token to all shift,
  pay-rate, and analytics requests and refuses user-data requests without one.
- M3 slice 7 is complete: the owner-scoped analytics summary API loads profile
  timezone/currency, shifts, and pay rates through RLS repositories and returns
  the exact deterministic domain totals for a bounded date range.
- M3 slice 6 is complete: pay-rate management now includes partial update and
  delete, with same-owner locking, overlap checks that exclude the edited row,
  RLS-hidden not-found behavior, and protection for rates covering shifts.
- M3 slice 5 is complete: owner-scoped pay-rate list/create API operations
  validate effective periods, serialize same-owner writes with a transaction
  advisory lock, reject inclusive period overlaps, and rely on RLS isolation.
- M3 slice 4 is complete: manual shift CRUD now includes partial update and
  delete, merged updates re-run full timezone/domain validation, nullable notes
  can be cleared explicitly, and RLS-hidden rows consistently return not found.
- M3 slice 3 is complete: authenticated shift list/create service and API paths
  use request-local RLS, derive `work_date` from the owner's profile timezone,
  validate domain rules, and never accept or expose an owner override.
- M3 slice 2 is complete: schedule aggregation now provides total paid hours,
  estimated pay, deterministic shift-type counts, and longest consecutive
  workday runs while counting multiple same-day shifts only once.
- M3 slice 1 is complete: framework-independent schedule calculations cover
  elapsed and paid duration, local work dates, DST changes, breaks,
  effective-dated pay rates, overlap/missing-rate rejection, and cent rounding.
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

Begin M4 with the smallest upload-validation and temporary-file-cleanup slice;
do not provision or call any paid service without a separate approval.

## Known risks

- Free-tier limits and provider policies can change; verify official policies
  again before provisioning in later milestones.
- Docker Desktop's CLI directory was not automatically present in this shell's
  PATH; the README documents the macOS PATH fallback.
- Docker bind mounts intermittently returned EIO for macOS compressed/file-provider
  metadata. The complete M3 gates ran against an identical local temporary copy;
  Git diff and frontend checks also passed directly against the working tree.
- The Supabase project now contains the M2 schema. Future migration changes must
  preserve compatibility between Alembic's direct migration path and the
  transaction-pooled runtime path.
