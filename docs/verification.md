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
