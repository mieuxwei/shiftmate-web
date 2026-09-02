# Project state

Last updated: 2026-09-02

## Current position

- Last completed milestone: **M0 — Repository boundary and Codex context**
- Next milestone: **M1 — Full-stack and Docker foundation**
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

## Next task packet

Use `docs/codex-task-template.md` to define one M1 vertical slice. M1 may add the
React/TypeScript/Vite frontend, FastAPI health endpoint, local toolchains,
single-container Docker foundation, and validation CI. Do not begin M2 services
or provision external resources during M1.

## Known risks

- Free-tier limits and provider policies can change; verify official policies
  again before provisioning in later milestones.
- Application and test commands do not exist until M1.
