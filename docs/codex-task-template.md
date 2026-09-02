# Codex task packet

Copy this packet for each internal implementation slice and replace every
placeholder. Keep one concrete outcome per packet and do not span multiple
milestones. Completing a packet is not a handoff boundary: continue with the
next packet in the same milestone until the complete milestone gate passes or
user input is required.

```text
Milestone: Mx
Objective: One concrete outcome for this task
In scope: Files and modules that may change
Out of scope: Areas this task must not touch
Acceptance: Observable and testable completion conditions
Verification: Exact commands or manual checks
Risk level: routine | elevated
```

Before starting, read `docs/project-state.md`, inspect `git status`, and read the
relevant implementation and tests. Record useful slice verification as work
continues. Only hand off when the complete milestone gate passes or a user
decision, approval, credential, external action, or other non-inferable input
is required. At handoff, update `docs/project-state.md` and
`docs/verification.md` without duplicating the full project plan.

#### Current progress (2026-09-03)

- Six typed read-only tools reuse shift, analytics, policy, assistant, and ICS
  application services; tool arguments expose neither owner override nor SQL.
- stdio authenticates from a process-only Supabase user token. Streamable HTTP
  is bearer-protected, Host/Origin checked, JSON-only, 64 KiB bounded, and
  stateless across restarts and instances.
- Every operation opens a fresh authenticated-role transaction with the
  verified owner claim, retaining PostgreSQL RLS as the data boundary.
- Structured audit events record tool/outcome/duration/request and a hashed
  owner reference without tokens, arguments, schedules, policy text, or output.
- Inspector and Python client demo instructions are documented. All tests use
  synthetic data; no live credential, model call, paid resource, or cloud
  provisioning was used.

#### Acceptance gate

- MCP 與 REST 相同 input 產生一致結果。
- Tool 無 raw SQL 或 owner override。
- 未授權 request 被拒絕。
- Tools 在重啟／scale-to-zero 後不依賴記憶體 session。

#### Codex usage

Elevated at tool contract and auth boundary；bounded security review complete.
