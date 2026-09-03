# ADR 0002: Database roles and connection pooling

- Status: Accepted
- Date: 2026-09-02

## Context

Ordinary API requests must preserve PostgreSQL RLS and must never use the
Supabase `service_role` HTTP key. Cloud Run instances are autoscaled, so direct,
unbounded PostgreSQL connections would also risk exhausting the Free-plan
connection allowance.

## Decision

- Verify user access tokens locally against the project's asymmetric JWKS. Only
  tokens with the configured issuer/audience and `role=authenticated` enter the
  ordinary request path; `service_role` tokens are rejected.
- Use separate secrets for migrations and runtime. Migrations use the direct
  endpoint with the database owner. Runtime uses a dedicated `NOBYPASSRLS` login
  that may `SET ROLE authenticated`; it must not be a database owner, superuser,
  or service-role credential.
- Each user request opens one explicit transaction, executes `SET LOCAL ROLE
  authenticated`, and sets the transaction-local JWT `sub`. Repository code
  never accepts an owner override. Transaction end clears both values before a
  pooled connection can be reused.
- Cloud Run runtime traffic uses the Free Shared Pooler in transaction mode.
  Psycopg prepared statements are disabled. SQLAlchemy keeps a deliberately
  small pool (default 2, overflow 0) per instance. Migrations never use the
  transaction pooler.
- The internal scheduled-job path will use a separate, narrowly granted role;
  it is not part of ordinary request dependencies. Any future service-role use
  requires a new ADR and must not expose user CRUD repositories.

## Consequences

RLS remains the final owner boundary even when repository queries omit explicit
owner predicates. Pool capacity stays bounded, at the cost of possible request
queuing under load. Supabase role creation and JWKS compatibility must be
verified for every target environment.

## References

- [Supabase JWT verification and JWKS](https://supabase.com/docs/guides/auth/jwts)
- [Supabase database connection modes](https://supabase.com/docs/guides/database/connecting-to-postgres)
