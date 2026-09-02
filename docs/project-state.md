# Project state

Last updated: 2026-09-02

## Current position

- Last completed milestone: **M7 — Google Calendar and ICS**
- Active milestone: **None; M8 not started**
- Blockers: none

## Completed

- Confirmed this is the independent `shiftmate-web` GitHub repository.
- Added repository safety rules, ignore rules, environment placeholders, license,
  and a README skeleton.
- Added persistent project state, verification log, task template, initial ADR,
  and synthetic-data policy.
- Confirmed no earlier project files, runtime dependencies, secrets, or private
  sample data are present.
- Added a React/TypeScript/Vite demo shell that reports live FastAPI health.
- Added typed FastAPI settings, OpenAPI, health routing, tests, and static SPA
  serving for the production bundle.
- Added the multi-stage production image, Compose workflows, pinned frontend
  lockfile, Python and TypeScript quality gates, and GitHub Actions validation.
- Verified the production image serves the React UI, health API, OpenAPI, and
  docs as a non-root user on local Docker.
- Verified both the production-like Compose service and the dev Vite-to-FastAPI
  proxy workflow; pnpm dependencies use isolated named volumes.

## Latest milestone

- M7 is complete: Google Calendar uses a web-server authorization-code flow
  with PKCE, an encrypted short-lived HttpOnly state cookie, validated local
  redirects, offline incremental authorization, and the narrow
  `calendar.events.owned` scope.
- Refresh tokens are encrypted with a distinct environment-provided key; access
  tokens remain request-local. Revoked or corrupt tokens produce bounded safe
  states and never change confirmed shift truth.
- Sync is serialized per owner and uses deterministic Google-compatible event
  IDs, owner/shift uniqueness, retry metadata, and deletion tombstones. Repeated
  or uncertain create/update/delete operations do not create duplicate events.
- Authenticated users can always export owner-scoped shifts as RFC 5545 ICS,
  including when OAuth is unconfigured or Google is unavailable. The UI exposes
  connection state, visible-range sync, errors, and ICS download.

- M6 is complete: a typed, stateless LangGraph normalizes each request, routes
  deterministic-first across schedule, policy, hybrid, and unsupported nodes,
  validates evidence, and composes bounded responses without a checkpointer or
  process-local conversational memory.
- Schedule facts, hours, consecutive days, and estimated pay come only from the
  owner-scoped deterministic analytics service. Policy citations come only from
  owner-scoped pgvector retrieval. The LLM never receives raw SQL or authority
  to calculate or write confirmed data.
- Hybrid consecutive-day analysis requires schedule rows, retrieved citations,
  and one unambiguous parseable rule threshold. Missing shifts, missing policy,
  unsupported rules, or conflicting thresholds produce an explicit refusal
  instead of a compliance conclusion.
- The responsive assistant UI shows route, tool status, deterministic facts,
  citations, refusal state, and a legal/HR/payroll disclaimer. A ten-case
  synthetic offline routing fixture covers all four routes, English/Traditional
  Chinese, writes, raw SQL, and prompt-injection-like input.
- M4 is complete: authenticated users can upload a JPG, PNG, or PDF into an
  owner-isolated import draft, review the structured candidates beside a local
  source preview, edit and explicitly confirm individual rows, then commit only
  valid confirmed rows into `shifts`.
- Extension, declared MIME, magic bytes, 5 MB size, PDF validity, and the 40-page
  limit are enforced. Server filenames are generated, uploads are deleted after
  each request, and the application logs neither file/model content nor tokens.
- `schedule_extraction_v1` uses a strict Pydantic/JSON schema and the configured
  `gemini-2.5-flash` adapter. Invalid, missing, DST-ambiguous, and nonexistent
  local times fail validation; quota/timeout/unavailable/invalid-output states
  use bounded error codes and allow a fresh upload retry.
- Draft creation commits before the external model call. Import item order and
  the item-to-shift link have database constraints; row locking plus that link
  makes repeated or concurrent commits idempotent.
- The synthetic offline OCR fixture covers nine required case families and
  reports exact date/time, missing/extra, schema-valid, and review-recall metrics.
- M5 adds owner-isolated policy PDF indexing and management, per-page cleaning
  and chunking, normalized 768-dimensional Gemini embeddings, a LangChain
  retriever over pgvector, relevance-threshold refusal, grounded answers, and
  database-derived page citations.
- Owner+SHA-256 uniqueness handles repeated/concurrent uploads. Retrieved text
  is delimited as untrusted evidence, and policy upload requires confirmation
  that the file is synthetic or anonymized.
- The synthetic RAG fixture covers answerable, unanswerable, conflicting,
  version-sensitive, and prompt-injection-like cases and reports Recall@k,
  citation correctness, groundedness, refusal accuracy, latency, and call count.

## Next task packet

Begin M8 with the read-only MCP transport and shared application-service
adapters, then continue through its complete gate. Keep Calendar export shared
with REST and MCP, and stop before any paid resource or live credential action.

## Known risks

- Free-tier limits and provider policies can change; verify official policies
  again before provisioning in later milestones.
- Docker Desktop's CLI directory was not automatically present in this shell's
  PATH; the README documents the macOS PATH fallback.
- Docker bind mounts intermittently returned EIO for macOS compressed/file-provider
  metadata. The complete M3 gates ran against an identical local temporary copy;
  Git diff and frontend checks also passed directly against the working tree.
- The Supabase project now contains the M2 schema. Future migration changes must
  preserve compatibility between Alembic's direct migration path and the
  transaction-pooled runtime path.
- The Gemini request shape is covered with a mocked official REST contract, but
  a live call was intentionally not made because no user credential was supplied.
- Google OAuth and Calendar REST shapes are covered with synthetic contract
  tests. A deployment must register its exact callback URI and provide five
  distinct secret/config values before live connection testing.
