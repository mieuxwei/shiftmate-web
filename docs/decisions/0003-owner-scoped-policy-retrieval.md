# ADR 0003: Owner-scoped policy retrieval

- Status: accepted
- Date: 2026-09-02

## Context

M5 needs LangChain-compatible semantic retrieval while preserving the existing
`policy_documents` and `policy_chunks` schema, PostgreSQL row-level security,
and transaction-scoped authenticated identity. Letting a generic vector-store
integration create and own separate tables would duplicate the planned schema
and could bypass the application's RLS boundary.

## Decision

- Store 768-dimensional, normalized Gemini embeddings in
  `policy_chunks.embedding` and index them with pgvector cosine distance.
- Implement the retriever as a LangChain `BaseRetriever` over the application
  tables. Every query runs on the request's authenticated SQLAlchemy connection,
  filters on `app_private.current_user_id()`, and remains protected by forced RLS.
- Construct citations from retrieved database metadata, not model-generated
  identifiers. Retrieved text is delimited as untrusted evidence in a versioned
  grounded-answer prompt.
- Run retrieval with an explicit no-op callback manager so a deployment's global
  LangChain/LangSmith tracing settings cannot export questions or policy text.
- Refuse before answer generation when no chunk meets the configured relevance
  threshold. Gemini quota failures affect indexing/new answers but not existing
  document listing or the rest of the application.
- Treat `(owner_id, sha256)` as the duplicate-document identity. Concurrent
  duplicate inserts converge through a database unique constraint.

## Consequences

The application keeps one owner-isolated source of truth and uses LangChain's
retriever/document contracts without granting schema-creation privileges at
request time. Changing embedding dimensions later requires a migration and
re-indexing existing policy chunks.
