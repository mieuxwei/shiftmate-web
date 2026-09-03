# Architecture and evidence map

ShiftMate keeps language-model output outside the system of record. Identity,
calculation, authorization, validation, and confirmed writes remain deterministic.
The public interactive demo is an additional static path: it reads only versioned
synthetic fixtures bundled into the frontend.

## System architecture

```mermaid
flowchart LR
  Demo[Public interactive demo] -->|/#demo| Fixture[Versioned synthetic fixtures]
  User[Authenticated user] --> SPA[React + TypeScript SPA]
  SPA -->|Bearer JWT| API[FastAPI application]
  Client[MCP client] -->|Bearer JWT| MCP[Stateless read-only MCP]
  MCP --> Services[Application services]
  API --> Services
  Services -->|authenticated role + owner claim| DB[(PostgreSQL + RLS + pgvector)]
  Services --> Gemini[Gemini structured output / embeddings]
  Services --> Calendar[Google Calendar API]
  Services --> ICS[In-memory ICS export]
  GitHub[GitHub Actions] -->|branch-restricted WIF| Run[Cloud Run]
  Run --> API
  Scheduler[Cloud Scheduler + OIDC] --> API

  classDef boundary fill:#e8f0eb,stroke:#315c48,color:#12261c;
  class Fixture,Services,DB boundary;
```

Key boundaries:

- The demo route never signs in, fetches production data, calls Gemini or
  Calendar, or exposes a write control.
- FastAPI verifies Supabase identity; PostgreSQL RLS derives the owner from the
  request transaction. Ordinary traffic does not use a service-role key.
- Gemini can propose import candidates or compose grounded text. It cannot
  execute SQL, calculate payroll, or confirm a shift.
- Calendar sync is optional and idempotent. ICS export remains available without
  OAuth and never writes to Google Calendar.
- GitHub deploys through Workload Identity Federation; no service-account JSON
  key is stored in the repository or GitHub.

## Data model

The diagram focuses on relationships relevant to the product. Every owner table
is protected by forced RLS; `scheduled_job_runs` is maintenance-only.

```mermaid
erDiagram
  PROFILES ||--o{ SHIFTS : owns
  PROFILES ||--o{ PAY_RATES : owns
  PROFILES ||--o{ SHIFT_IMPORTS : owns
  SHIFT_IMPORTS ||--o{ SHIFT_IMPORT_ITEMS : contains
  SHIFT_IMPORT_ITEMS o|--o| SHIFTS : commits_to
  PROFILES ||--o{ POLICY_DOCUMENTS : owns
  POLICY_DOCUMENTS ||--o{ POLICY_CHUNKS : contains
  PROFILES ||--o{ CALENDAR_CONNECTIONS : owns
  SHIFTS ||--o{ CALENDAR_SYNC_RECORDS : syncs
  PROFILES ||--o{ CHAT_SESSIONS : owns
  CHAT_SESSIONS ||--o{ CHAT_MESSAGES : contains
  PROFILES ||--o{ TOOL_AUDIT_LOGS : owns

  PROFILES { uuid id PK }
  SHIFTS { uuid id PK uuid owner_id FK date work_date timestamptz start_at timestamptz end_at }
  PAY_RATES { uuid id PK uuid owner_id FK numeric hourly_rate date effective_from date effective_to }
  SHIFT_IMPORTS { uuid id PK uuid owner_id FK text status text prompt_version }
  SHIFT_IMPORT_ITEMS { uuid id PK uuid import_id FK uuid owner_id FK text validation_status }
  POLICY_DOCUMENTS { uuid id PK uuid owner_id FK text status int page_count }
  POLICY_CHUNKS { uuid id PK uuid document_id FK uuid owner_id FK int page_number vector embedding }
  CALENDAR_CONNECTIONS { uuid id PK uuid owner_id FK text encrypted_refresh_token text status }
  CALENDAR_SYNC_RECORDS { uuid id PK uuid shift_id FK uuid owner_id FK text external_event_id text status }
  CHAT_SESSIONS { uuid id PK uuid owner_id FK }
  CHAT_MESSAGES { uuid id PK uuid session_id FK uuid owner_id FK text selected_route }
  TOOL_AUDIT_LOGS { uuid id PK uuid owner_id FK text tool_name text result_status }
```

## LangGraph assistant

```mermaid
flowchart TD
  Start([Question]) --> Normalize[Normalize question]
  Normalize --> Route{Deterministic route first}
  Route -->|schedule| Schedule[Load deterministic schedule facts]
  Route -->|policy| Policy[Retrieve owner-scoped policy chunks]
  Route -->|hybrid| Hybrid[Load facts + policy evidence]
  Route -->|unsupported| Unsupported[Prepare bounded refusal]
  Schedule --> Validate[Validate required evidence]
  Policy --> Validate
  Hybrid --> Validate
  Unsupported --> Validate
  Validate -->|sufficient| Compose[Compose bounded answer]
  Validate -->|missing / conflicting| Refuse[Refuse with reason]
  Compose --> End([Answer + route + tool trace + citations])
  Refuse --> End
```

The graph is stateless and has no checkpointer. Schedule totals, pay estimates,
and consecutive-day counts come from deterministic services. Policy citations
are assembled from stored document, chunk, and page metadata rather than
invented by a model.

## Deployment and removal

Production is a single container in Cloud Run (`min 0`, `max 1`, request-based
CPU, 512 MiB) backed by the existing Supabase PostgreSQL project. The complete
resource inventory, migration path, rollback procedure, emergency stop, and
ordered teardown are documented in [deployment.md](deployment.md). No automatic
database downgrade is performed during rollback.
