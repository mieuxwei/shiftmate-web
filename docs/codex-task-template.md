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

- API/MCP Gemini calls share a durable daily cap; owner uploads have a durable
  daily quota, and a bounded process-local limiter protects the max-one-instance
  HTTP deployment.
- Safe errors and structured logs exclude credentials, bodies, query strings,
  document content, owner identifiers, and raw exception messages.
- `daily-maintenance` verifies Google OIDC, uses a narrow NOLOGIN database role,
  and claims a unique logical run date so duplicate delivery is a no-op.
- Versioned Cloud Run/Artifact/Scheduler/IAM policies and the zero-cost runbook
  define request-based/min0/max1/no-GPU/no-VPC controls, cleanup, budgets, stop,
  and teardown. No cloud resource or paid feature was created.

#### Acceptance gate

- Duplicate scheduled invocation 無副作用。
- Unauthorized internal endpoint request 失敗。
- Cloud Run config 明確為 request-based/min0/max1/no GPU/no VPC connector。
- Artifact cleanup 將 production + rollback 預估 storage 控制在 0.5 GiB 內。
- 無未批准 GCP resources。

#### Codex usage

Elevated；bounded IAM/cost review complete.
