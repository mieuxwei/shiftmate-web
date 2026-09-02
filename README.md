# ShiftMate Web

ShiftMate Web is a responsive portfolio application for managing personal
shifts, estimating work hours and pay, importing synthetic schedules with an
LLM-assisted review flow, and answering questions grounded in synthetic work
policy documents.

The project is being built from scratch as an independent repository. It does
not contain or depend on the earlier `line-bot-calendar` project.

## Current status

Milestone M0 is complete. The next milestone is M1: the React, FastAPI, Docker,
and validation foundation. See [`docs/project-state.md`](docs/project-state.md)
for the concise handoff and [`projectplan.md`](projectplan.md) for the complete
execution specification.

No application runtime exists yet.

## Product boundaries

- Use only synthetic or anonymized schedules, rates, policies, and screenshots.
- Do not use the application for legal, HR, payroll, or employment decisions.
- Keep secrets in local environment variables or platform secret stores.
- Target an expected cloud cost of NT$0 and fail closed when free quotas end.

## Planned stack

- React, TypeScript, and Vite
- FastAPI and typed Python domain services
- PostgreSQL, Supabase Auth, RLS, and pgvector
- Gemini, LangChain, LangGraph, RAG, and read-only MCP tools
- Docker, GitHub Actions, and a single Cloud Run service

## Development

M1 will add runnable development commands. Until then, M0 can be inspected with:

```bash
git status --short --branch
git ls-files
```

Configuration names are documented in `.env.example`; never commit `.env` or
real credentials.

## License

[MIT](LICENSE)
