# Project state

Last updated: 2026-09-02

## Current position

- Last completed milestone: **M1 — Full-stack and Docker foundation**
- Next milestone: **M2 — PostgreSQL, Auth and RLS**
- Active milestone: none
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

## Next task packet

Use `docs/codex-task-template.md` to define one M2 vertical slice. Start with the
smallest locally verifiable database/migration boundary and owner-isolation test
foundation. Do not provision Supabase or any potentially paid resource without
checking current free-tier terms and obtaining approval when required.

## Known risks

- Free-tier limits and provider policies can change; verify official policies
  again before provisioning in later milestones.
- Docker Desktop's CLI directory was not automatically present in this shell's
  PATH; the README documents the macOS PATH fallback.
