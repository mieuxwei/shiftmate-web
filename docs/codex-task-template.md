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
