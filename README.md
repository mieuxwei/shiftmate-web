# ShiftMate Web

**A deterministic-first, LLM-assisted shift management portfolio project.**

[Live app](https://shiftmate-web-fucvnupudq-de.a.run.app/) ·
[3-minute Reviewer Showcase](https://shiftmate-web-fucvnupudq-de.a.run.app/#reviewer) ·
[2.5-minute video](https://github.com/mieuxwei/shiftmate-web/releases/download/v1.0.0/shiftmate-demo.mp4) ·
[OpenAPI](https://shiftmate-web-fucvnupudq-de.a.run.app/docs) ·
[Evaluation report](evals/reports/summary.md)

ShiftMate explores a practical question: how can an AI assistant help with
schedule images and policy questions without becoming the authority for hours,
pay, identity, or confirmed writes? The answer is a deliberately narrow model
boundary backed by typed services, PostgreSQL RLS, human confirmation, visible
refusals, and reproducible offline evaluation.

The application is an independent repository and does not contain, import, or
depend on the earlier `line-bot-calendar` project.

## Review it in three minutes

Open the public **Reviewer Showcase**. It is a five-step, read-only tour built
from versioned local fixtures: no login, production database query, Gemini or
Calendar call, account creation, or write control is involved.

1. Dashboard results: overnight shifts, work hours, effective-dated pay estimate.
2. AI import: structured candidates, invalid-row warning, human-confirmed write.
3. Policy RAG: page citation plus a visible low-confidence/conflict refusal.
4. LangGraph assistant: route, tool trace, deterministic facts, grounded answer.
5. System evidence: Calendar/ICS, MCP, RLS, WIF, Cloud Run, CI, and evaluation.

The speaking notes are in [the demo script](docs/demo-script.md). The existing
bright synthetic product demo remains available from the homepage.

![ShiftMate reviewer video: deterministic results and safety boundary](docs/images/reviewer-video-01.png)

## What is implemented

- Responsive React/TypeScript schedules, charts, dashboard, pay-rate CRUD, and
  deterministic hours/pay analytics with timezone and overnight-shift handling.
- Gemini-assisted JPG/PNG/PDF schedule extraction into an owner-scoped draft;
  schema validation, editing, and explicit row confirmation precede idempotent
  writes.
- Owner-scoped policy PDF indexing with LangChain, pgvector retrieval, bounded
  grounded answers, document/page citations, and evidence-based refusals.
- Stateless LangGraph routing across schedule, policy, hybrid, and unsupported
  paths. LLMs cannot calculate pay, execute SQL, or write confirmed shifts.
- Optional idempotent Google Calendar sync using the narrow
  `calendar.events.owned` scope, encrypted refresh tokens, and an ICS fallback.
- Six authenticated, owner-scoped, read-only MCP tools over stdio and stateless
  Streamable HTTP.
- FastAPI, PostgreSQL forced RLS, Docker, GitHub Actions, branch-restricted WIF,
  bounded Cloud Run, authenticated Cloud Scheduler, quotas, and safe logging.

See the [architecture, ERD, and LangGraph diagrams](docs/architecture.md) for the
complete boundary map.

## Evidence, including failures

Every named portfolio technology maps to repository evidence rather than a
screenshot-only claim.

| Capability | Repository evidence |
| --- | --- |
| React + TypeScript | `frontend/src`, responsive tests, Vitest, ESLint, TypeScript build |
| FastAPI + OpenAPI | `backend/app/api`, typed schemas, `/docs`, backend tests |
| PostgreSQL + SQL + pgvector + RLS | `migrations`, integration tests, policy retrieval services |
| Gemini + LangChain + RAG | versioned prompts/adapters, policy services, offline fixtures |
| LangGraph | deterministic-first graph and routing tests in `backend/app/services/assistant.py` |
| MCP | six typed read-only tools, two transports, auth/RLS parity tests, [usage guide](docs/mcp.md) |
| Calendar | PKCE OAuth, encrypted token storage, idempotent sync, ICS fallback tests |
| Docker + GitHub Actions | multi-stage image, Compose, validate/release workflows |
| Cloud Run + Scheduler + WIF | versioned deployment policies, smoke scripts, [operations guide](docs/deployment.md) |

The offline suite intentionally keeps observed misses visible:

- OCR: 9 synthetic cases, 3 failed cases; date exact match 0.889, time exact
  match 0.778, review recall 0.80.
- RAG: 5 synthetic cases, 1 failed conflict case; Recall@k 0.90, citation
  correctness 1.00, groundedness 0.80, refusal accuracy 0.80.
- Routing: 12 synthetic questions, 2 conservative ambiguous fallbacks; accuracy
  0.833.

These small synthetic fixtures are reproducible directional evidence, not a
production benchmark or traffic telemetry. The [full generated report](evals/reports/summary.md)
lists every failure, limitation, and deterministic provider-failure test.

## API and integrations

OpenAPI is served by the deployed application. Safe REST and MCP examples are
in [OpenAPI and MCP examples](docs/api-examples.md); the complete MCP transport
and Inspector guide is in [docs/mcp.md](docs/mcp.md).

Gemini and Google Calendar are optional. Without their configuration, the
system fails closed with bounded states; existing confirmed shifts remain
unchanged, and ICS export remains available. Upload only synthetic or
anonymized schedules and policies.

## Run locally

Requirements: Python 3.12, Node.js 24, pnpm 11.19, and Docker.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
corepack enable
pnpm --dir frontend install --frozen-lockfile
docker compose up --build
curl --fail http://localhost:8000/api/v1/health
```

Open <http://localhost:8000>. The public reviewer and synthetic demo need no
credential. Authenticated CRUD requires the public Supabase URL and anonymous
key; never expose a service-role key to Vite. All supported configuration names
are documented in `.env.example`.

Run the principal gates:

```bash
ruff format --check .
ruff check .
mypy
pytest --cov=backend.app --cov-report=term-missing
python evals/run.py --check
pnpm --dir frontend format
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
docker build -t shiftmate-web:local .
```

Disposable PostgreSQL integration commands are documented in
[`AGENTS.md`](AGENTS.md). Production resource inventory, migrations, deployed
verification, rollback, emergency stop, and exact removal order are in
[docs/deployment.md](docs/deployment.md).

## Boundaries and trade-offs

- This is a portfolio demonstration, not a production HR, payroll, legal, or
  employment-decision system. Pay is explicitly an estimate.
- All public examples, screenshots, fixtures, narration, and evaluation inputs
  are synthetic. Never send private schedules, payroll records, or internal
  policy documents to Gemini Free Tier.
- Model output is probabilistic. Import candidates require validation and human
  confirmation; RAG refuses low-relevance or conflicting evidence.
- Process-local rate limiting is intentional for the configured maximum of one
  Cloud Run instance; horizontal scaling would require a shared limiter.
- The deployed target is designed for expected NT$0 operation, not an absolute
  billing guarantee. Cloud Run scales from zero to at most one instance, quotas
  fail closed, retention is bounded, and spending alerts are not instantaneous
  hard caps.
- Supabase, Gemini, GitHub, and GCP free-tier policies can change. No paid plan,
  add-on, voice service, or anonymous production write is required by the demo.

Milestone state and verification history are in [docs/project-state.md](docs/project-state.md)
and [docs/verification.md](docs/verification.md). The full implementation plan
and acceptance gates are in [projectplan.md](projectplan.md).

## License

[MIT](LICENSE)
