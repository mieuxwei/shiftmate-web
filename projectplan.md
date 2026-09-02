# ShiftMate Web — Codex Execution Plan

> 全新網頁版 LLM 智慧班表助理｜AI Application Developer Portfolio Project

## 0. Codex 必讀指令

本文件是新專案 `shiftmate-web` 的執行規格與單一規劃來源（source of truth）。Codex 在實作前必須完整閱讀本文件，並遵循以下規則。

### 0.1 規範詞彙

- **MUST**：不可省略；不符合即不得宣告 milestone 完成。
- **SHOULD**：原則上必須做到；若偏離，必須記錄理由與替代方案。
- **MAY**：選配項，不得阻塞必要成果。

### 0.2 執行規則

1. MUST 建立全新 repository；不得修改、搬移、匯入或依賴原 `line-bot-calendar` 專案。
2. MUST 一次只執行一個 active milestone；不得同時展開多個大型 milestone。
3. MUST 在編碼前檢查目前狀態、相關檔案與既有測試，不得假設 repository 狀態。
4. MUST 以最小且可驗證的 vertical slice 作為 milestone 內部檢查點，再擴充下一片；slice 完成不得視為停止或 handoff 條件。
5. MUST 使用既有穩定函式庫與清楚的 application boundary，不為展示而自行重造框架。
6. MUST 在 milestone 完成前執行該 milestone 的驗收命令並記錄結果。
7. MUST 保護使用者既有檔案與未提交變更；不得執行 destructive Git 操作。
8. MUST 把 secrets 放在環境變數或平台 secret store，不得寫入 repository。
9. MUST 使用合成或匿名資料；Gemini Free Tier 不得處理真實私人班表、薪資或公司內部文件。
10. MUST 以預期雲端費用 NT$0 為目標；任何可能導致付費的變更都需要先停下並取得使用者批准。
11. MUST 在功能與計畫發生偏差時先更新本文件或 ADR，再繼續實作。
12. MUST 僅在需要使用者決策／批准／憑證／外部操作等無法安全推定的輸入，或完整 milestone gate 通過時停止並 handoff；單一 task packet、slice 或 targeted test 完成後 MUST 在同一次執行中直接繼續該 milestone。測試失敗時，只要仍有範圍內的修復或診斷路徑，也不得因此停止。
13. MUST 在 milestone gate 通過後等待使用者明確批准該 milestone 的 commit/push；一旦批准，Codex 應自行提交所有已驗證變更並推送目前 branch 至既有 upstream，不需再次詢問。不得 rewrite remote history；push 失敗時只能使用安全、非破壞性的修復方式。
14. MUST 在允許停止時提供簡短 handoff：變更檔案、驗證結果、未解風險，以及需要的確切決策或下一個 milestone。

### 0.3 Codex 使用量治理

本專案以 Codex 為主要實作者，但 MUST 避免不必要的大量額度消耗。

#### 預設低使用量模式

日常工作預設採以下做法：

- 使用 `rg`、檔案清單與精準行號定位，只讀取目前 milestone 需要的檔案。
- 不在每次任務重新掃描或重新解釋整個 repository。
- 不重複生成已存在的架構、schema、README 或測試。
- 不同時產出多個功能版本；先實作本文件指定的預設方案。
- 優先執行 targeted tests；只有 milestone gate、release gate 才跑完整 test suite。
- 優先使用 deterministic code、formatter、type checker、migration tool 與測試工具處理機械工作。
- 對簡單 scaffold、CRUD、樣式與文件同步使用一般推理強度。
- 不為例行工作啟動平行 agent 或獨立 reviewer。
- commentary 與 handoff 保持精簡，不輸出無助於決策的逐步內部過程。

#### 允許提高嚴謹度的關卡

下列工作 MAY 提高推理強度，或安排一個範圍明確的獨立 review；其餘工作維持低使用量模式：

- PostgreSQL schema、Alembic migration 與資料完整性設計。
- Supabase Auth、RLS、Google OAuth、token storage 與權限邊界。
- LangGraph state、tool routing、human confirmation 與 retry semantics。
- MCP tool contract、寫入安全與 REST/MCP 一致性。
- RAG retrieval、citation、prompt injection 防護與 evaluation 設計。
- Cloud Run、IAM、Workload Identity Federation、Artifact Registry 與費用控制。
- 無法由 targeted tests 定位的跨層錯誤。
- milestone completion review 與 `v1.0.0` release review。

提高嚴謹度前 MUST 先寫清楚：

1. 要解決的風險。
2. 需要檢查的檔案或介面。
3. 預期產物。
4. 停止條件。

若使用獨立 review，MUST 限定為單一 bounded task，例如「只檢查 RLS 是否能阻止跨使用者讀取」，不得要求另一個 agent 重新分析整個專案。

#### 防止重複消耗的持久化上下文

新 repository MUST 維護：

- `docs/project-state.md`：目前 milestone、已完成內容、阻塞、下一步。
- `docs/decisions/`：Architecture Decision Records（ADR）。
- `docs/verification.md`：已執行的關鍵測試與 deployment checks。
- `docs/codex-task-template.md`：每次交給 Codex 的精簡 task packet。

Codex 開始工作時 SHOULD 先讀上述狀態檔與相關程式，而不是重新推導全案。

### 0.4 Codex task packet

後續每個 milestone 及其內部 slice 請使用下列格式，降低重新理解成本。Task packet 是內部執行檢查點，不是停止邊界；完成後應建立下一個同 milestone packet 並持續執行，直到符合第 12 條停止條件：

```text
Milestone: Mx
Objective: 本次只完成的一個具體成果
In scope: 允許修改的模組
Out of scope: 本次不可碰的內容
Acceptance: 可觀察、可測試的完成條件
Verification: 要執行的命令或人工檢查
Risk level: routine | elevated
```

---

## 1. 專案身份與硬性界線

### 1.1 專案定義

- 名稱：**ShiftMate Web**
- Repository：`shiftmate-web`
- 產品型態：responsive web application
- 核心定位：結合結構化班表、非結構化規章、LLM、RAG 與 tool use 的 AI application
- 主要使用者：管理個人輪班、工時與工作規章的使用者
- 主要介面：React web UI
- 主要後端：FastAPI
- 正式執行環境：單一 Cloud Run service
- 正式資料庫：Supabase Free PostgreSQL + pgvector
- LLM：Gemini Developer API Free Tier

### 1.2 原專案隔離

新專案 MUST：

- 使用全新目錄與全新 GitHub repository。
- 使用獨立 GCP project、Supabase project、Gemini key 與 Google OAuth credentials。
- 不呼叫原 Vercel URL。
- 不修改原 LINE Bot、GAS trigger、Google Sheet、Calendar 或 secrets。
- 不把原專案放進 `legacy/`、Git submodule 或 fixtures。
- 不複製原專案內硬編碼姓名、時薪、情緒規則與私人資料。
- 僅延續「班表圖片辨識、人工確認、工時計算、Calendar 同步」的產品概念，程式與資料模型重新設計。

### 1.3 零成本原則

- GCP Billing account 已獲使用者接受，但預期帳單 MUST 維持 NT$0。
- 免費額度耗盡時，系統 MUST fail closed、停用或降級，不得自動切換付費資源。
- 不使用 Cloud SQL、付費 GPU、付費模型、付費向量 DB、付費 observability、付費 OCR、付費 email/SMS。
- 不啟用 Artifact Registry vulnerability scanning 等會產生額外費用的功能。
- 新增任何 GCP/SaaS resource 前 MUST 記錄其免費條件、刪除方式與用量上限。

---

## 2. 產品成果

### 2.1 核心使用流程

#### A. 班表圖片／PDF 匯入

1. 使用者上傳 JPG、PNG 或 PDF。
2. FastAPI 建立持久化 import draft。
3. Gemini multimodal model 回傳 structured output。
4. Pydantic 與 domain validator 檢查日期、時間、跨日、缺漏與異常。
5. React 顯示逐筆 review table、warnings 與原始來源。
6. 使用者修改或確認。
7. 只有 confirmed items 可寫入正式 `shifts`。

#### B. 班表與薪資管理

- 月／週班表檢視。
- 手動 CRUD。
- 總工時、晚班數、連續工作日與預估薪資。
- 時薪具有有效期間，不硬編碼。
- 所有數值由 deterministic Python code 計算，不由 LLM 心算。

#### C. RAG 規章問答

- 上傳合成員工手冊、請假規定、排班政策或 SOP。
- PDF 解析、清理、chunking、embedding、pgvector retrieval。
- Gemini 依 retrieved context 回答。
- 每個可回答結果顯示文件、頁碼與引用段落。
- 無充分證據時明確回覆資料不足。

#### D. SQL + RAG 混合分析

問題範例：

> 我這週有沒有違反文件裡的連續工作規定？

LangGraph MUST：

1. 使用 SQL/application tool 取得班表。
2. 使用 RAG retriever 取得規章。
3. 使用 deterministic evaluator 計算班表事實。
4. 驗證資料與引用。
5. 由 Gemini 整理結論、限制與 citation。

UI MUST 標示這是作品示範，不構成法律、人資或薪資建議。

#### E. Google Calendar

- Google OAuth 2.0 authorization-code flow。
- incremental authorization 與最小 Calendar scope。
- 可建立、更新、刪除同步 event。
- 保存 external event ID 與 sync status。
- 同步錯誤可安全重試，不破壞正式班表。
- 未授權或 API 不可用時提供 `.ics` export。

#### F. MCP tools

第一版提供 read-only tools：

- `get_shifts`
- `calculate_work_hours`
- `get_payroll_summary`
- `search_work_policy`
- `analyze_schedule_compliance`
- `create_calendar_export`

REST 與 MCP MUST 共用相同 application services。

### 2.2 Dashboard

Dashboard MUST 至少呈現：

- 指定期間總工時。
- 預估薪資。
- 班別分布。
- 每週工時趨勢。
- 連續工作日提示。
- 最近 import 與 Calendar sync status。

### 2.3 明確不做

- LINE Bot 與 GAS。
- 自動產生最佳排班。
- 真實勞動法合規判定。
- 付款、訂閱與商業計費。
- 模型 fine-tuning。
- 自行訓練 OCR 模型。
- 真實私人班表、薪資或公司機密文件。
- Kubernetes、Kafka 或拆成多個微服務。

---

## 3. 技術覆蓋與選型

| 技術面 | MUST 實際用途 | 驗收證據 |
|---|---|---|
| Python | domain、ETL、FastAPI、AI workflow | typed modules + pytest |
| TypeScript | React、API client、UI state | strict type-check |
| React + Vite | 完整網頁與 dashboard | production build |
| FastAPI | REST、auth dependencies、OpenAPI、MCP HTTP | `/docs` + API tests |
| Gemini | Vision extraction、routing 輔助、grounded response、embedding | structured schema + eval |
| Prompt Engineering | extraction/router/RAG/hybrid prompts | versioned prompt files |
| LangChain | loader、splitter、retriever、RAG chain | integration tests |
| LangGraph | SQL/RAG/hybrid/unsupported graph | state graph + route tests |
| RAG | 規章問答與 citations | retrieval/grounding report |
| PostgreSQL | 班表、費率、imports、documents、audit | Alembic migrations |
| SQL | repositories、analytics、constraints | query tests |
| pgvector | embeddings 與 vector search | similarity query |
| Data cleansing | OCR 日期時間標準化與 rejected rows | validation report |
| ETL pipeline | upload → parse → validate → review → commit | import state machine |
| Dashboard | 工時、薪資、班別與同步狀態 | React page |
| Google Calendar API | OAuth 與 event sync | integration/demo |
| MCP | read-only ShiftMate tools | Inspector/client demo |
| Docker | multi-stage production container | local + CI image build |
| Git/GitHub | issues、branches、PR、tags | repository history |
| GitHub Actions | tests、image build、deploy | green workflows |
| GCP Cloud Run | 正式 full-stack container | public HTTPS URL |
| Cloud Scheduler | 一個 authenticated maintenance job | job run record |
| Artifact Registry | 保存目前 production image | same-region image |
| Supabase | Free PostgreSQL、pgvector、Auth | RLS + DB tests |
| Security | JWT、RLS、OAuth state、IAM、rate limits | security tests/checklist |
| AI evaluation | OCR、retrieval、grounding、routing | reproducible reports |

### 3.1 不重複堆疊替代工具

- React 取代 Streamlit。
- pgvector 取代 Chroma/FAISS。
- FastAPI 取代 Flask。
- Cloud Run 取代 Vercel production hosting。
- Supabase PostgreSQL 取代 Cloud SQL，因 Cloud SQL 會增加固定付費風險。
- Cloud Scheduler 取代 GAS/Vercel Cron；只建立一個 job，保持在每個 billing account 三個免費 jobs 的範圍內。
- LangGraph 與 LangChain 都 MUST 有實際角色，不得只是安裝 dependency。

---

## 4. 目標架構

```text
Browser
┌─────────────────────────────────────────────┐
│ React + TypeScript                          │
│ Schedule / Import / Chat / Policies / Stats │
└─────────────────────┬───────────────────────┘
                      │ same-origin HTTPS
                      ▼
┌─────────────────────────────────────────────────────┐
│ Cloud Run — one request-based container             │
│ FastAPI serves REST, MCP HTTP and built React assets │
├─────────────────────────────────────────────────────┤
│ Application Services                                │
│ Shift / Payroll / Import / Policy / Calendar        │
├─────────────────────────────────────────────────────┤
│ LangGraph                                           │
│ Route → SQL | RAG | Hybrid | Unsupported            │
├──────────────┬──────────────────┬───────────────────┤
│ Gemini       │ LangChain RAG    │ MCP adapters      │
│ Vision/LLM   │ + pgvector       │ shared services   │
└──────┬───────┴────────┬─────────┴─────────┬─────────┘
       │                │                   │
       ▼                ▼                   ▼
 Gemini Free      Supabase Free      Google Calendar
 Tier             PostgreSQL/Auth    API / ICS

Cloud Scheduler ──OIDC──> /internal/jobs/daily-maintenance
GitHub Actions ───WIF───> Artifact Registry ──> Cloud Run
```

### 4.1 架構原則

- React production build MUST 由同一個 container 提供，避免維護兩個 paid-risk runtime。
- 前端與 API SHOULD same-origin，降低 CORS 與 OAuth complexity。
- Domain layer MUST 不依賴 FastAPI、LangChain、Gemini 或 Supabase client。
- LLM MUST 不直接執行 SQL、計算薪資或寫入 confirmed data。
- REST 與 MCP MUST 只作 transport adapters。
- Cloud Run filesystem MUST 視為 ephemeral；資料只存 PostgreSQL，暫存檔 request 後刪除。
- 背景工作不得依賴 request 結束後仍執行 CPU；需要排程的內容由 Cloud Scheduler 呼叫明確 endpoint。

---

## 5. Repository 結構

```text
shiftmate-web/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── schedule/
│   │   │   ├── imports/
│   │   │   ├── assistant/
│   │   │   ├── policies/
│   │   │   └── dashboard/
│   │   ├── api/
│   │   └── types/
│   ├── tests/
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── domain/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── integrations/
│   │   │   ├── gemini.py
│   │   │   └── google_calendar.py
│   │   ├── ai/
│   │   │   ├── prompts/
│   │   │   ├── extraction/
│   │   │   ├── rag/
│   │   │   └── workflows/
│   │   └── mcp/
│   └── tests/
├── migrations/
├── evals/
│   ├── ocr/
│   ├── retrieval/
│   ├── grounded_answers/
│   └── routing/
├── sample_data/
│   ├── schedules/
│   └── policies/
├── docs/
│   ├── project-state.md
│   ├── verification.md
│   ├── codex-task-template.md
│   ├── architecture.md
│   ├── data-model.md
│   ├── prompts.md
│   ├── evaluation.md
│   ├── zero-cost-operations.md
│   └── decisions/
├── scripts/
├── infra/
│   ├── cloud-run/
│   └── scheduler/
├── .github/workflows/
├── AGENTS.md
├── Dockerfile
├── compose.yaml
├── pyproject.toml
├── .env.example
├── projectplan.md
└── README.md
```

新 repo 不得存在原專案的 `legacy/` copy。

---

## 6. 資料模型與安全界線

### 6.1 必要 tables

#### `profiles`

- `id`：Supabase Auth user ID
- `display_name`
- `timezone`
- `currency`
- timestamps

#### `shifts`

- `id`, `owner_id`
- `work_date`
- `start_at`, `end_at`
- `break_minutes`
- `shift_type`, `notes`
- `source`：manual/import/calendar
- timestamps

`end_at` MUST 晚於 `start_at`；跨日使用 timestamp，不使用 `24:00` 字串。

#### `pay_rates`

- `id`, `owner_id`
- `hourly_rate`
- `effective_from`, `effective_to`

#### `shift_imports`

- `id`, `owner_id`
- `filename`, `media_type`, `sha256`
- `status`：uploaded/extracting/review/committed/failed/expired
- `model_name`, `prompt_version`
- `error_code`
- timestamps

#### `shift_import_items`

- `id`, `import_id`, `owner_id`
- raw structured payload
- normalized shift fields
- `validation_status`, `warnings`
- `confirmed_at`

#### `policy_documents`

- `id`, `owner_id`
- `title`, `filename`, `sha256`
- `status`, `page_count`
- timestamps

#### `policy_chunks`

- `id`, `document_id`, `owner_id`
- `content`, `page_number`, `chunk_index`
- `metadata` JSONB
- `embedding` vector

#### `calendar_connections`

- `id`, `owner_id`
- encrypted refresh token
- scopes、expiry/revocation status
- timestamps

#### `calendar_sync_records`

- `id`, `shift_id`, `owner_id`
- external event ID
- sync status、last error code、retry count
- timestamps

#### `chat_sessions`, `chat_messages`

- owner/session/role/content
- selected route
- cited chunk IDs
- tool calls
- latency/usage metadata
- MUST NOT 保存 hidden chain-of-thought

#### `tool_audit_logs`

- actor、tool name
- sanitized arguments
- result status
- confirmation status
- timestamps

#### `scheduled_job_runs`

- job name、logical run date
- status、idempotency key
- timestamps

### 6.2 資料庫要求

- 所有 user-owned tables MUST 啟用 RLS。
- 一般 request MUST 使用使用者 JWT；不得使用 service-role key 繞過 owner boundary。
- MUST 測試兩個 user 無法互讀、互改資料。
- `shifts(owner_id, work_date)` MUST 有 index。
- `scheduled_job_runs(job_name, logical_run_date)` MUST 有 unique constraint。
- pgvector 小資料先使用 exact search；有實測需要才加入 HNSW。
- migrations MUST 可從空 DB 完整重建，不接受手動 dashboard-only schema。

---

## 7. API、LangGraph 與 MCP contract

### 7.1 REST API

```text
GET    /api/v1/health
GET    /api/v1/shifts
POST   /api/v1/shifts
PATCH  /api/v1/shifts/{shift_id}
DELETE /api/v1/shifts/{shift_id}

POST   /api/v1/imports
GET    /api/v1/imports/{import_id}
PATCH  /api/v1/imports/{import_id}/items/{item_id}
POST   /api/v1/imports/{import_id}/commit

POST   /api/v1/policies
GET    /api/v1/policies
DELETE /api/v1/policies/{document_id}

POST   /api/v1/assistant/query
GET    /api/v1/analytics/summary

GET    /api/v1/calendar/connect
GET    /api/v1/calendar/callback
POST   /api/v1/calendar/sync
GET    /api/v1/calendar/export.ics

POST   /internal/jobs/daily-maintenance
```

### 7.2 LangGraph

```text
START
  → normalize_question
  → route_intent
      ├── schedule_query → schedule service/tool
      ├── policy_query   → LangChain retriever
      ├── hybrid_query   → schedule + retrieval + rule evaluator
      └── unsupported    → bounded response
  → validate_evidence
  → compose_answer
  → END
```

Routing SHOULD 先用 deterministic rules；只有模糊問題才呼叫 LLM classifier。

### 7.3 MCP

- MUST 支援本機 stdio demo。
- SHOULD 提供適合 Cloud Run 的 stateless Streamable HTTP endpoint；不得依賴單一 instance memory session。
- 第一版 MUST read-only。
- tools MUST 不接受 raw SQL。
- tool arguments MUST 經 Pydantic、owner 與日期範圍驗證。
- MCP 與 REST 對相同 input MUST 產生語意一致結果。

---

## 8. AI、RAG 與 evaluation 規格

### 8.1 Versioned prompts

MUST 建立：

- `schedule_extraction_v1`
- `intent_router_v1`
- `rag_answer_v1`
- `hybrid_compliance_v1`

每份 prompt MUST 記錄目的、input/output schema、禁止行為、edge cases、version 與對應 eval cases。

### 8.2 Schedule extraction

Structured output MUST 包含：

- 日期、開始時間、結束時間。
- 是否跨日。
- 班別與備註。
- `needs_review`。
- warnings。

模型不得生成 DB ID、薪資、總工時或合規結論。

### 8.3 RAG pipeline

```text
PDF
→ file validation
→ text extraction with page metadata
→ cleaning
→ chunking
→ Gemini free embedding
→ pgvector
→ owner-filtered retrieval
→ score threshold
→ grounded prompt
→ answer + citations
```

Retrieved document text MUST 視為不可信資料，不得覆蓋 system instruction 或取得 tools/secrets。

### 8.4 Evaluation

#### OCR dataset

至少包含合成案例：清楚圖片、陰影、歪斜、跨夜、空白／休假、多人、多日期、標記、模糊而應 review。

MUST 計算：

- 日期 exact match。
- start/end time exact match。
- missing/extra shift rate。
- schema-valid rate。
- `needs_review` recall。

#### RAG dataset

至少包含：answerable、unanswerable、conflicting sections、version-sensitive、prompt-injection-like text。

MUST 計算或人工 rubric：

- Recall@k。
- citation correctness。
- groundedness。
- refusal accuracy。
- latency 與 Gemini call count。

#### Routing dataset

MUST 驗證 schedule/policy/hybrid/unsupported 四類問題走正確 branch。

Evaluation MUST 使用本機 Python/pytest/JSON/Markdown，不依賴付費平台。

---

## 9. Cloud Run 與零成本操作規格

### 9.1 Cloud Run service

正式 deployment MUST：

- 使用 request-based billing。
- `min-instances=0`。
- `max-instances=1`；若未來需要提高，必須先取得批准。
- 不使用 GPU。
- 不使用 Serverless VPC Connector。
- 不使用 instance-based billing 或 always-on CPU。
- 使用最低能穩定完成 OCR/RAG request 的 CPU/memory，經測試後記錄 ADR。
- 設定 request timeout、upload limit、rate limit 與 Gemini daily cap。
- 使用 single container：multi-stage build 先編譯 React，再由 FastAPI 提供 static assets。
- Artifact Registry 與 Cloud Run 放在同一 region。

### 9.2 Artifact Registry

- MUST 只保留目前 production image 與最多一個 rollback image。
- MUST 設 cleanup policy，總 storage 目標小於官方 0.5 GiB free allowance。
- MUST 不啟用 billable vulnerability scanning。
- image MUST 使用 multi-stage build、`.dockerignore` 與小型 base image。

### 9.3 CI/CD

GitHub Actions MUST：

1. 執行 backend lint/type-check/tests。
2. 執行 frontend lint/type-check/tests/build。
3. build production Docker image。
4. main branch release gate 通過後，使用 Workload Identity Federation 登入 GCP。
5. push Artifact Registry。
6. deploy Cloud Run。
7. 執行 production health smoke test。

MUST 不保存長期 service-account JSON key。

### 9.4 Cloud Scheduler

- 只建立一個 job：`daily-maintenance`。
- 使用 OIDC/IAM 呼叫 authenticated Cloud Run internal endpoint。
- job MUST idempotent，重複執行不得重複資料。
- job 只做 expired draft cleanup、stale status cleanup 與小型 maintenance；不得執行長時間 embedding batch。
- 建立更多 job 前 MUST 確認 billing account 仍在三個免費 jobs 範圍並取得批准。

### 9.5 費用控制

- MUST 建立 GCP budget notifications。
- 若帳戶可用 Cloud Run spend cap preview，SHOULD 設置 service/project spend cap；仍不可只依賴 alert。
- MUST 記錄停用／刪除 Cloud Run、Scheduler、Artifact Registry 的操作步驟。
- MUST 在 `docs/zero-cost-operations.md` 記錄每項資源、free allowance、用量檢查位置與清理方式。
- MUST 在 deployment milestone 人工檢查 Billing report。
- MUST 不建立 Cloud SQL、Cloud Storage bucket、Load Balancer、Cloud NAT 或其他未列入本規格的 GCP 資源。

### 9.6 其他免費服務

- Supabase MUST 維持 Free organization，不開 add-on。
- Gemini MUST 使用 Free Tier project，不切換 pay-as-you-go。
- GitHub repository SHOULD public，以使用免費 standard Actions runners。
- Google Calendar 使用量 MUST 保持展示規模；政策改變時以 `.ics` 為無費用 fallback。

### 9.7 官方依據（2026-09-02 核對）

- [Cloud Run pricing](https://cloud.google.com/run/pricing)：request-based free tier 包含免費 requests、CPU 與 memory allowance。
- [Cloud Run billing settings](https://docs.cloud.google.com/run/docs/configuring/billing-settings)：request-based 只在處理 request、startup 與 shutdown 時計費。
- [Cloud Run scaling](https://docs.cloud.google.com/run/docs/configuring)：minimum/maximum instances 可控制 scale-to-zero 與成本風險。
- [Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing)：每個 billing account 前 0.5 GiB-month storage 免費。
- [Cloud Scheduler pricing](https://cloud.google.com/scheduler/pricing)：每個 billing account 每月三個 jobs 免費。
- [Supabase billing](https://supabase.com/docs/guides/platform/billing-on-supabase)：Free Plan 提供有限額度 PostgreSQL/Auth/Storage。
- [Supabase pgvector](https://supabase.com/docs/guides/database/extensions/pgvector)：可使用 `vector` extension 儲存 embeddings。
- [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)：Developer API 提供 Free Tier。
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)：公開 repo 的 standard runners 免費。
- [Google Calendar API quotas](https://developers.google.com/workspace/calendar/api/guides/quota)：標準使用目前在配額內不額外收費，實作前須再次核對政策。

---

## 10. 安全與可靠性規格

### 10.1 Secrets 與 identity

- `.env`、Gemini key、Supabase keys、OAuth credentials MUST 不進 Git。
- 只提交 placeholder `.env.example`。
- frontend 只可使用 Supabase anon key。
- 一般 request 不得用 Supabase service-role key。
- Google refresh token MUST encrypted at rest。
- GitHub → GCP MUST 使用 WIF，不得使用 service-account JSON key。
- Cloud Scheduler → Cloud Run MUST 使用 OIDC/IAM。

### 10.2 Upload security

- 驗證 extension、MIME type、magic bytes。
- 單檔上限 5 MB；PDF 上限 40 頁。
- 拒絕 archive、executable 與未知格式。
- server 重新生成 filename。
- request 後清理 temp files。
- logs 不得記錄完整文件、圖片、token 或模型 raw content。

### 10.3 LLM/tool security

- 文件與圖片內容一律是不可信資料。
- 模型不得生成或執行 raw SQL。
- mutation 需要 idempotency key 或 unique constraint。
- 第一版 MCP tools read-only。
- 錯誤回應只顯示安全 error code。
- hidden chain-of-thought 不保存、不回傳。

### 10.4 Reliability

- Import MUST 使用 draft/review/commit state machine。
- Calendar sync MUST 可重試且不重複 event。
- Scheduled job MUST 用 unique logical run key。
- Gemini quota exhausted 時，手動班表與 SQL dashboard MUST 仍可用。
- Embedding quota exhausted 時，既有文件 retrieval SHOULD 仍可用。
- Calendar unavailable 時 MUST 提供 ICS。
- Supabase unavailable 時 MUST 顯示 unavailable；不得假裝寫入成功。

---

## 11. Milestones

Milestone 只描述依賴、產物與 gate，不包含日期或完成天數。任何時候最多一個 milestone 標記為 `IN_PROGRESS`。

### Status legend

- `NOT_STARTED`
- `IN_PROGRESS`
- `BLOCKED`
- `COMPLETE`

### Milestone register

| ID | Milestone | Depends on | Status |
|---|---|---|---|
| M0 | Repository boundary and Codex context | — | COMPLETE |
| M1 | Full-stack and Docker foundation | M0 | COMPLETE |
| M2 | PostgreSQL, Auth and RLS | M1 | COMPLETE |
| M3 | Schedule domain and Dashboard | M2 | COMPLETE |
| M4 | Gemini schedule import ETL | M3 | COMPLETE |
| M5 | LangChain RAG and citations | M2 | COMPLETE |
| M6 | LangGraph hybrid assistant | M3, M5 | COMPLETE |
| M7 | Google Calendar and ICS | M3 | COMPLETE |
| M8 | MCP Server | M3, M5, M6 | COMPLETE |
| M9 | Security, scheduling and cost controls | M4, M5, M7, M8 | COMPLETE |
| M10 | AI evaluation and reliability | M4, M5, M6 | NOT_STARTED |
| M11 | Cloud Run CI/CD deployment | M9, M10 | NOT_STARTED |
| M12 | Portfolio release | M11 | NOT_STARTED |

### M0 — Repository boundary and Codex context

#### Objective

建立完全獨立、可由 Codex 持續低成本接手的 repository 與狀態文件。

#### Deliverables

- New `shiftmate-web` repo。
- `projectplan.md` copied to repo root。
- `AGENTS.md`：濃縮不可違反規則與常用驗證命令。
- `.gitignore`, `.env.example`, license, README skeleton。
- `docs/project-state.md`, `docs/verification.md`, `docs/codex-task-template.md`。
- `docs/decisions/0001-new-independent-web-project.md`。
- Synthetic-data policy。

#### Acceptance gate

- Repo 不含原專案檔案、URL、secrets 或私人資料。
- `git status` clean。
- Secret scan 無發現。
- `docs/project-state.md` 指向 M1，且沒有重述整份計畫。

#### Codex usage

Routine。不得啟動額外 reviewer。

### M1 — Full-stack and Docker foundation

#### Objective

建立 React、FastAPI、單一 production container 與最小 CI。

#### Deliverables

- React + TypeScript + Vite。
- FastAPI health endpoint、settings、OpenAPI。
- Multi-stage Dockerfile：build React → Python runtime。
- Compose local workflow。
- Python/TypeScript lint、format、type-check、tests。
- GitHub Actions validation workflow。

#### Acceptance gate

- Local frontend/API 可啟動。
- Container 可在本機提供 UI 與 `/api/v1/health`。
- Backend unit test、frontend test、type-check、Docker build 全部成功。
- 無 Supabase、Gemini 或 GCP credentials 也能進入 documented demo/dev state。

#### Codex usage

Routine。只在 container build 無法定位時提高推理。

### M2 — PostgreSQL, Auth and RLS

#### Objective

建立可重建的 schema、Supabase Auth 與 owner isolation。

#### Deliverables

- Alembic migrations。
- profiles、shifts、pay_rates、imports、policy、calendar、audit、job tables。
- pgvector extension migration。
- JWT validation dependency。
- RLS policies。
- Repository interfaces 與 integration tests。
- ADR：service-role usage policy、connection pooling strategy。

#### Acceptance gate

- 空 DB 可由 migration 建立完整 schema。
- downgrade/upgrade strategy 有測試或明確限制。
- User A 無法讀寫 User B 資料。
- 普通 API request 不使用 service-role bypass。
- Constraints 與 indexes 經測試。

#### Codex usage

Elevated。完成後 MAY 安排一個 bounded schema/RLS review。

### M3 — Schedule domain and Dashboard

#### Objective

完成不依賴 LLM 的核心產品 vertical slice。

#### Deliverables

- Shift CRUD service/API/UI。
- Month/week schedule views。
- Pay-rate management。
- Work-hours/payroll/consecutive-days deterministic calculators。
- Dashboard summary charts。
- Synthetic demo dataset。

#### Current progress (2026-09-02)

- Deterministic schedule/pay calculations, owner-scoped shift and pay-rate CRUD,
  and the analytics summary API are implemented and verified.
- The frontend now has a testable Supabase session gateway and typed authenticated
  client for the M3 API surface.
- Month/week views, dashboard summaries/charts, shift and pay-rate mutation UI,
  and the credential-free synthetic read-only demo are implemented and verified.
- The complete M3 acceptance gate passed on 2026-09-02; milestone status is
  `COMPLETED`, and the user approved its commit and push.

#### Acceptance gate

- 手動 CRUD 可用且受 owner isolation 保護。
- 跨日、break、費率期間與 timezone tests 通過。
- Dashboard 數字與 service 計算一致。
- Gemini unavailable 時此 milestone 的功能仍完整可用。

#### Codex usage

Routine。優先 targeted unit/component tests。

### M4 — Gemini schedule import ETL

#### Objective

完成 upload → structured extraction → validate → review → commit。

#### Deliverables

- Upload validation 與 temp-file cleanup。
- Gemini adapter 與 model config。
- Versioned extraction prompt/schema。
- Persistent import state machine。
- Review/edit/commit UI。
- Idempotent commit。
- OCR eval fixtures。

#### Current progress (2026-09-02)

- Upload validation, Gemini structured extraction, persistent review state,
  explicit per-item confirmation, idempotent commit, review UI, and the offline
  OCR evaluation gate are implemented.
- The complete M4 acceptance gate passed on 2026-09-02. No live Gemini call,
  paid service, private schedule, or secret was used during verification.

#### Acceptance gate

- 未確認項目不會進 `shifts`。
- Invalid/ambiguous time 會拒絕或標記 `needs_review`。
- 重複 commit 不會重複班表。
- Gemini error/quota 狀態清楚且可重試。
- Logs 不含原始圖片或完整模型內容。

#### Codex usage

Routine implementation；schema validation 與 prompt/eval gate 可使用 elevated reasoning。

### M5 — LangChain RAG and citations

#### Objective

建立 user-isolated、可引用、可拒答的 RAG。

#### Deliverables

- PDF extraction with page metadata。
- Cleaning/chunking pipeline。
- Gemini embedding adapter。
- LangChain pgvector retriever。
- Grounded answer chain。
- Document management UI。
- Citation component。
- Retrieval fixtures。

#### Current progress (2026-09-02)

- Owner-scoped PDF extraction/chunking, 768-dimensional Gemini embeddings,
  pgvector cosine retrieval through a LangChain `BaseRetriever`, grounded
  answering/refusal, database-derived page citations, SHA-256 deduplication,
  document UI, and synthetic offline RAG evaluation are implemented.
- The complete M5 acceptance gate passed locally against disposable PostgreSQL
  17 + pgvector and the production container. No live Gemini call, private
  document, credential, paid service, or cloud resource was used.

#### Acceptance gate

- User A 無法 retrieve User B chunks。
- Answerable questions 有正確 citation。
- Unanswerable questions 能拒答。
- Prompt-injection-like document text 不可改變 system/tool policy。
- 文件重複上傳依 SHA-256 處理。

#### Codex usage

Elevated at retriever/security design and completion review；其餘 routine。

### M6 — LangGraph hybrid assistant

#### Objective

以真實 graph 協調 schedule、policy、hybrid 與 unsupported 問題。

#### Deliverables

- Typed graph state。
- Deterministic-first router。
- Schedule, RAG, hybrid, unsupported nodes。
- Evidence validator。
- Response composer。
- Chat UI 與 citation/tool display。
- Route test dataset。

#### Acceptance gate

- 四類問題 route tests 通過。
- 工時與薪資由 deterministic service 回傳。
- Hybrid answer 同時具有班表 facts 與規章 citations。
- 缺資料時不產生合規結論。
- Graph 不依賴 process-local conversational memory。

#### Codex usage

Elevated。MUST 在 graph contract 固定後再實作 UI；完成後 MAY bounded review state/retry semantics。

### M7 — Google Calendar and ICS

#### Objective

提供安全 Calendar OAuth sync 與零授權 fallback。

#### Deliverables

- OAuth state/PKCE 或適合 web-server flow 的安全實作。
- Incremental Calendar scope。
- Encrypted token storage。
- Create/update/delete sync service。
- Sync status/retry model。
- ICS exporter。

#### Current progress (2026-09-02)

- Web-server authorization-code flow uses PKCE plus an encrypted, ten-minute,
  HttpOnly state cookie bound to the owner and a validated local return path.
- Offline incremental authorization requests only
  `calendar.events.owned`; refresh tokens use a separate at-rest encryption key
  and access tokens remain request-local.
- Owner-serialized create/update/delete sync uses stable provider-valid event
  IDs, retry metadata, revoked-token states, and deletion tombstones so repeated
  or uncertain sync does not duplicate events.
- RFC 5545 ICS export remains available without OAuth configuration and is
  generated only from owner-scoped confirmed shifts.
- The authenticated UI exposes connection state, visible-range sync, revoked
  authorization guidance, and an always-available ICS download.
- OAuth/provider calls are contract-tested with synthetic responses; no live
  credentials, Calendar data, paid resource, or cloud provisioning was used.

#### Acceptance gate

- OAuth state/redirect validation tests 通過。
- Calendar repeated sync 不重複 event。
- Revoked token 產生可理解狀態。
- 未連 Calendar 可使用 ICS。
- Calendar failure 不修改 confirmed shift truth。

#### Codex usage

Elevated for OAuth/token boundary；一般 UI routine。完成後 SHOULD security review。

### M8 — MCP Server

#### Objective

將既有 services 以標準化 tools 暴露，不複製 business logic。

#### Deliverables

- MCP stdio entrypoint。
- Stateless HTTP transport if compatible with Cloud Run constraints。
- Six read-only tools。
- Typed inputs/outputs。
- Audit logging。
- MCP Inspector/client demo instructions。

#### Acceptance gate

- MCP 與 REST 相同 input 產生一致結果。
- Tool 無 raw SQL 或 owner override。
- 未授權 request 被拒絕。
- Tools 在重啟／scale-to-zero 後不依賴記憶體 session。

#### Codex usage

Elevated at tool contract and auth boundary；完成後 MAY bounded MCP security review。

### M9 — Security, scheduling and cost controls

#### Objective

完成 production 前的安全、排程、idempotency 與成本防護。

#### Deliverables

- Rate limits、upload quotas、Gemini daily cap。
- Safe error mapping、structured logs、PII redaction。
- One Cloud Scheduler maintenance job design。
- OIDC/IAM policy。
- Artifact cleanup policy。
- Cloud Run min/max/billing config files/scripts。
- `docs/zero-cost-operations.md`。
- GCP budget/spend-cap checklist。

#### Completion notes

- Durable owner upload quotas and an application-wide Gemini request cap are
  enforced before external model calls across REST and MCP; the HTTP surface
  also has a bounded max-one-instance rate limiter and safe structured errors.
- `daily-maintenance` verifies Google-signed OIDC claims, uses a narrow NOLOGIN
  database role, claims a unique logical date, and safely skips duplicates.
- Versioned Cloud Run, Artifact Registry cleanup, Scheduler, IAM, validation,
  budget, incident-stop, and teardown policies define the zero-cost envelope.
- The complete M9 gate passed on 2026-09-03 with synthetic local tests only. No
  GCP resource, live credential, private data, paid feature, or model call was
  used.

#### Acceptance gate

- Duplicate scheduled invocation 無副作用。
- Unauthorized internal endpoint request 失敗。
- Cloud Run config 明確為 request-based/min0/max1/no GPU/no VPC connector。
- Artifact cleanup 將預期 storage 控制在 0.5 GiB 內。
- 無未批准 GCP resources。

#### Codex usage

Elevated。完成後 MUST bounded IAM/cost review。

### M10 — AI evaluation and reliability

#### Objective

以可重跑證據驗證 OCR、RAG、routing 與降級行為。

#### Deliverables

- OCR evaluation report。
- RAG retrieval/grounding report。
- Routing report。
- Failure-mode tests：Gemini/Supabase/Calendar unavailable。
- Evaluation command documented。

#### Acceptance gate

- Reports 由版本化 fixtures 重建。
- 指標、sample count、限制與失敗案例可見。
- 不只挑選成功案例。
- Evaluation 不依賴 paid platform。

#### Codex usage

Elevated for metric design and failure analysis；資料整理/報告生成 routine。

### M11 — Cloud Run CI/CD deployment

#### Objective

用無長期 GCP key 的 CI/CD 部署 single-container full-stack app。

#### Deliverables

- Artifact Registry same-region repo。
- GitHub OIDC/WIF。
- Deploy service account least privilege。
- Cloud Run service。
- Cloud Scheduler job。
- Production migrations procedure。
- Post-deploy health/smoke workflow。
- Rollback and teardown procedures。

#### Acceptance gate

- Main release workflow 全綠。
- Public HTTPS app 可完成核心 demo。
- Cloud Run min0/max1/request-based verified from deployed config。
- Billing report 與 Artifact storage 人工確認。
- 無 service-account JSON key。
- Teardown instructions 經 dry-run review。

#### Codex usage

Elevated。MUST 使用最小變更、逐項驗證；不得平行建立多套 deployment。

### M12 — Portfolio release

#### Objective

將已驗證成果整理為可快速理解、可重現、沒有誇大的作品。

#### Deliverables

- README。
- Architecture diagram、ERD、LangGraph diagram。
- OpenAPI 與 MCP usage examples。
- Evaluation summaries。
- Screenshots 與 demo script/video。
- Local Docker、Cloud deployment、teardown instructions。
- Limitations、privacy、free-tier caveats。
- Release tag `v1.0.0`。

#### Acceptance gate

- 新 reviewer 能從 README 理解 problem、architecture、demo、tests 與 trade-offs。
- README 不宣稱法律判定或 production HR readiness。
- 每項履歷技術都有 repository 證據。
- CI、Docker build、production smoke test 全綠。
- `docs/project-state.md` 標示 COMPLETE，無未揭露 blocker。

#### Codex usage

Routine documentation；release gate MAY 使用一個 bounded final review。

---

## 12. 驗證層級

Codex MUST 依成本由低到高執行驗證：

### Level 1 — 每次小改動

- Formatter。
- 受影響模組 lint/type-check。
- 受影響 unit tests。

### Level 2 — Feature completion

- Feature integration tests。
- Relevant frontend tests/build。
- Migration/query checks if applicable。

### Level 3 — Milestone gate

- Backend full tests。
- Frontend full tests/type-check/build。
- Docker build/smoke。
- Security/eval subset defined by milestone。
- 更新 `docs/verification.md`。

### Level 4 — Release/deployment gate

- Full CI。
- Migration verification。
- Production deployment smoke。
- Billing/resource configuration check。
- RAG/OCR/routing reports。

不得為每個 CSS、copy 或 isolated unit change 執行 Level 4。

---

## 13. Definition of Done

只有同時符合以下條件才可建立 `v1.0.0`：

- 原專案完全未修改，新專案無 runtime dependency。
- M0–M12 全部 `COMPLETE`。
- Python、TypeScript、React、FastAPI、Gemini、LangChain、LangGraph、RAG、PostgreSQL、SQL、pgvector、MCP、Docker、GitHub Actions、Cloud Run、Cloud Scheduler、Calendar 與 Dashboard 都有可執行成果。
- OCR、RAG、routing 都有可重跑 evaluation。
- 所有 LLM 寫入前有人工確認或 read-only 限制。
- 無 hard-coded secret、真實私人資料或未揭露 paid dependency。
- Cloud Run 已驗證 request-based、min0、max1、無 GPU、無 VPC connector。
- Artifact Registry storage 控制在免費 allowance 目標內。
- Supabase 與 Gemini 維持 Free Tier。
- 配額耗盡時 fail closed，不自動付費。
- README 清楚揭露隱私、費用、技術限制與非法律建議。
- CI、Docker build、production health/smoke 全部通過。

---

## 14. 下一個獲准動作

本文件只授權規劃調整。開始實作前，Codex 應取得使用者對「建立全新 `shiftmate-web` 專案」的明確指示，然後只執行 M0。

建議的第一個 Codex task packet：

```text
Milestone: M0
Objective: 建立全新 shiftmate-web repository skeleton 與 Codex 持久化狀態文件
In scope: 新專案目錄、Git 初始化、規劃與安全文件
Out of scope: 原專案、React/FastAPI 程式、Supabase、Gemini、GCP deployment
Acceptance: M0 acceptance gate 全部通過
Verification: secret scan、repository file review、git status
Risk level: routine
```
