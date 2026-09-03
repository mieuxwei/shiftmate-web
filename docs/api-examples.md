# OpenAPI and MCP examples

The deployed interactive OpenAPI document is available at
<https://shiftmate-web-fucvnupudq-de.a.run.app/docs>. Except for health and the
static reviewer experience, product endpoints require a short-lived Supabase
user access token. Examples below use placeholders and synthetic dates only.

## REST API

```bash
curl --fail https://shiftmate-web-fucvnupudq-de.a.run.app/api/v1/health
```

Read the signed-in owner's shifts:

```bash
curl --fail \
  -H "Authorization: Bearer ${SHIFTMATE_ACCESS_TOKEN}" \
  "https://shiftmate-web-fucvnupudq-de.a.run.app/api/v1/shifts?date_from=2026-09-01&date_to=2026-09-07"
```

Ask the hybrid assistant. It returns the route, tool status, deterministic facts,
refusal state, and page citations:

```bash
curl --fail \
  -H "Authorization: Bearer ${SHIFTMATE_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"question":"我的班表有違反連續工作規定嗎？","date_from":"2026-09-01","date_to":"2026-09-07"}' \
  https://shiftmate-web-fucvnupudq-de.a.run.app/api/v1/assistant/query
```

Never put a real token in a checked-in script, screenshot, terminal recording,
or issue. The assistant cannot execute SQL or write a confirmed shift.

## MCP

The stdio and stateless Streamable HTTP transports expose the same six
owner-scoped, read-only tools:

```bash
export SHIFTMATE_MCP_ACCESS_TOKEN="your-short-lived-user-access-token"
python scripts/mcp_client_demo.py \
  --tool calculate_work_hours \
  --arguments '{"date_from":"2026-09-01","date_to":"2026-09-07"}'
```

No tool schema accepts `owner_id`, raw SQL, or a write operation. Transport
configuration, MCP Inspector steps, HTTP protection, and the tool list are in
[mcp.md](mcp.md).
