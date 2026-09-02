# Database migrations

Alembic is the only supported way to change the application schema. Set
`DATABASE_URL` to a PostgreSQL connection string and run:

```bash
alembic upgrade head
alembic downgrade base
```

The first two migrations build the complete planned M2 table set, pgvector,
constraints/indexes, and owner-isolation policies. M5 fixes policy embeddings at
768 dimensions, adds the cosine HNSW index, owner-scoped SHA-256 deduplication,
and bounded policy indexing errors. `scheduled_job_runs` is an
internal table: it has forced RLS but no authenticated-user policy or grant.

Downgrade removes application tables and the private identity helper. It leaves
the shared `pgcrypto` and `vector` extensions installed because they may predate
the application or be used by other schemas in a managed PostgreSQL project.

RLS derives the user UUID from PostgreSQL request JWT settings. Application code
must set those settings only after JWT validation. Direct database clients and
ordinary API requests must never accept an owner UUID as an authorization
override.
