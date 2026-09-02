# ADR 0001: Build an independent web project

- Status: Accepted
- Date: 2026-09-02

## Context

ShiftMate Web continues only the high-level product ideas of schedule image
recognition, human confirmation, deterministic work calculations, and calendar
sync. The earlier `line-bot-calendar` system may contain a different runtime,
private assumptions, integrations, or data that must not cross the new project
boundary.

## Decision

Build ShiftMate Web from scratch in the independent `shiftmate-web` repository.
Do not copy, modify, import, vendor, mount, or depend on the earlier project at
build time or runtime. Use separate cloud projects, databases, API keys, OAuth
credentials, URLs, test data, and deployment resources.

The target is one responsive React web application served with a FastAPI API
from a single Cloud Run container. Persistent data will live in a separate
Supabase PostgreSQL project. External resources are not provisioned by this ADR
or by M0.

## Consequences

- The codebase and schema will be implemented anew in later milestones.
- Migration from the earlier application is explicitly out of scope.
- Demonstrations and tests require purpose-built synthetic fixtures.
- Later integrations must document their independent resource boundary and
  zero-cost controls before provisioning.
