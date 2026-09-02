# ShiftMate Web

ShiftMate Web is a responsive portfolio application for managing personal
shifts, estimating work hours and pay, importing synthetic schedules with an
LLM-assisted review flow, and answering questions grounded in synthetic work
policy documents.

The project is being built from scratch as an independent repository. It does
not contain or depend on the earlier `line-bot-calendar` project.

## Current status

Milestones M1–M3 are complete. The application now includes the PostgreSQL/RLS
foundation, authenticated shift and effective-dated pay-rate CRUD, deterministic
hours/pay analytics, month/week schedules, dashboard charts, and a credential-free
synthetic read-only demo. M4 (Gemini schedule import ETL) is next. See
[`docs/project-state.md`](docs/project-state.md) for the concise handoff and
[`projectplan.md`](projectplan.md) for the complete execution specification.

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

Requirements: Python 3.12, Node.js 24, pnpm 11.19, and Docker with Compose.

On macOS, if Docker Desktop is running but `docker` is not yet on your shell
PATH, run this once in the current terminal:

```bash
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
```

Install the local dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
corepack enable
pnpm --dir frontend install --frozen-lockfile
```

Run the API and Vite frontend in separate terminals:

```bash
source .venv/bin/activate
uvicorn backend.app.main:app --reload
```

```bash
pnpm --dir frontend dev
```

Open `http://localhost:5173`. The Vite server proxies `/api` to FastAPI on port
8000. No external credentials are needed for the documented read-only demo:
select **查看合成資料示範** on the landing page. To use authenticated CRUD,
configure the public `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` values;
never expose a service-role key to Vite.

For the single-container production-like workflow, run:

```bash
docker compose up --build
curl --fail http://localhost:8000/api/v1/health
```

The built React UI and API are then both available from `http://localhost:8000`.
To run both hot-reload-oriented Compose services instead, use
`docker compose --profile dev up --build` and open port 5173.

Run the application checks with:

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
```

For the disposable M2 PostgreSQL integration checks:

```bash
docker compose --profile m2 up -d db
export M2_TEST_DATABASE_URL="postgresql+psycopg://postgres:shiftmate_local_only@localhost:5432/shiftmate_test"
pytest -m integration
docker compose --profile m2 down
```

Configuration names are documented in `.env.example`; never commit `.env` or
real credentials.

## License

[MIT](LICENSE)
