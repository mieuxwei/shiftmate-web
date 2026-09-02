# Read-only MCP server

ShiftMate exposes the same owner-scoped shift, analytics, policy, assistant,
and calendar-export application services through six MCP tools:

- `get_shifts`
- `calculate_work_hours`
- `get_payroll_summary`
- `search_work_policy`
- `analyze_schedule_compliance`
- `create_calendar_export`

Every tool is typed and read-only. No tool accepts an owner ID or raw SQL. The
caller is derived from a verified Supabase access token, and each database call
opens a fresh transaction with the `authenticated` role and the caller's RLS
claim. Audit events contain the tool, outcome, duration, request ID, and a
one-way shortened owner reference; they do not contain bearer tokens, tool
arguments, schedules, policy text, or results.

`get_payroll_summary` is an estimate only and is not legal, HR, or payroll
advice. `create_calendar_export` renders an ICS string in memory; it does not
write a file or create, update, or delete a calendar event.

## Required local configuration

Set the normal authenticated application configuration in your shell:

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export DATABASE_URL="postgresql+psycopg://..."
export DATABASE_REQUEST_ROLE="authenticated"
export SHIFTMATE_MCP_ACCESS_TOKEN="your-short-lived-user-access-token"
```

Policy search and policy-backed compliance analysis also require the existing
`GEMINI_API_KEY` configuration. Keep every real value in a local or platform
secret store. Never commit an access token, service-role key, private schedule,
payroll record, or internal policy document.

## stdio and client demo

Install the project as described in the README, then run the bundled stdio
entrypoint:

```bash
source .venv/bin/activate
python -m backend.app.mcp.server
```

The process reads `SHIFTMATE_MCP_ACCESS_TOKEN` from its environment. A missing,
invalid, expired, wrong-audience, or non-`authenticated` token makes every tool
call fail with `UNAUTHORIZED`.

The bundled client lists the tools without printing user data:

```bash
source .venv/bin/activate
python scripts/mcp_client_demo.py
```

To deliberately call a read-only tool with synthetic data:

```bash
python scripts/mcp_client_demo.py \
  --tool calculate_work_hours \
  --arguments '{"date_from":"2026-09-01","date_to":"2026-09-07"}'
```

## MCP Inspector

Use Node 22.19 or newer, start the current Inspector, and keep its process
bound to loopback:

```bash
npx @modelcontextprotocol/inspector
```

In the Inspector, add a stdio server with command
`<project>/.venv/bin/python`, arguments `-m backend.app.mcp.server`, working
directory `<project>`, and add
`SHIFTMATE_MCP_ACCESS_TOKEN` through the Inspector's secret environment-value
UI. Do not put a real token in a checked-in MCP configuration file. Connect,
open **Tools**, confirm exactly six tools, and run them only against synthetic or
anonymized data.

## Stateless Streamable HTTP

The normal FastAPI process mounts MCP at `http://localhost:8000/mcp/`:

```bash
source .venv/bin/activate
uvicorn backend.app.main:app
python scripts/mcp_client_demo.py --http http://localhost:8000/mcp/
```

The client sends `SHIFTMATE_MCP_ACCESS_TOKEN` as a bearer token. The endpoint
rejects missing or invalid authorization before MCP dispatch. It uses JSON
responses, a 64 KiB request limit, and stateless Streamable HTTP; there is no
in-memory conversational or MCP session required after restart, scale-to-zero,
or routing to another instance.

For a deployed hostname, set `MCP_ALLOWED_HOSTS` and `MCP_ALLOWED_ORIGINS` as
JSON arrays. Keep DNS-rebinding protection enabled by listing only the actual
service host and browser origins. Example local values are in `.env.example`.
