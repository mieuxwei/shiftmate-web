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

- One offline runner rebuilds versioned OCR, RAG, routing, and Markdown summary
  reports from synthetic fixtures, or fails when committed reports are stale.
- Reports expose sample counts, metrics, observed failures, and explicit
  limitations. Offline baselines intentionally include representative misses.
- Deterministic failure injection covers Gemini import failure, unavailable
  Supabase JWKS, and unavailable Google Calendar without accepting identity,
  creating shifts, or changing confirmed shift truth.
- CI verifies report freshness. No credential, private data, live model,
  external API, paid platform, or cloud resource was used.

#### Acceptance gate

- Reports 由版本化 fixtures 重建。
- 指標、sample count、限制與失敗案例可見。
- 不只挑選成功案例。
- Evaluation 不依賴 paid platform。

#### Codex usage

Elevated metric design and failure analysis complete; report generation routine.
