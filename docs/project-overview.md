# ShiftMate Web：專案介紹、現況與技術總覽

Independent AI Systems Project · v1.0.0 Released

以人工覆核 AI 班表草稿、確定性工時計算與附來源規章查詢為核心的輪班助理。

[English README](../README.md) · [Live Demo](https://shiftmate-web-fucvnupudq-de.a.run.app/#demo) · [系統架構](architecture.md) · [評估報告](../evals/reports/summary.md)

## 專案現況

2026-09-04 核對：GitHub 已有 [v1.0.0 Release](https://github.com/mieuxwei/shiftmate-web/releases/tag/v1.0.0)，發布於 2026-09-03，tag 指向 `9691ba5`。本機修改前的 main 為 `b401174`，比 tag 多一筆提交；版本發布事實與本次呈現修改分開紀錄。

本次是既有系統的文件、合成展示與前端互動優化。下列截圖來自本版本的實際頁面；原始 tag 之後的呈現更新透過[發布流程](https://github.com/mieuxwei/shiftmate-web/actions/workflows/release.yml)部署，線上版本可能在發布期間短暫落後 repo。專案並未宣告凍結；後端 API、schema、認證、RLS 與正式寫入流程不在本次修改範圍。

| 範圍          | 已實作內容                                                         | 使用邊界                                     |
| ------------- | ------------------------------------------------------------------ | -------------------------------------------- |
| 免登入 Demo   | 五步導覽、六筆明細、補正與確認、引用與衝突、助理拒絕寫入、證據入口 | 固定合成資料；狀態只存在前端記憶體           |
| 正式工作區    | 登入後管理班次與費率、匯入覆核、工時摘要、規章與整合               | 需自行配置帳號與服務憑證，不提供共用公開帳密 |
| AI 與外部整合 | Gemini、LangGraph、RAG、Calendar、MCP                              | 程式碼已實作；Demo 不呼叫這些服務            |
| 品質證據      | 版本化合成評估、單元測試、資料庫整合測試                           | 小樣本離線證據，不等於正式環境準確率或 SLA   |

## 解決什麼問題

輪班資料常從圖片開始，但辨識結果可能缺少時間；跨夜班與休息扣除容易算錯；工作規章可能有多個互相矛盾的版本。ShiftMate 將這些不確定性分開處理：

1. AI 只提出草稿，由格式驗證與人工確認守住寫入邊界。
2. 工時與預估薪資由確定性程式計算，不交由語言模型自行推算。
3. 規章回答必須回到文件片段與來源；證據不足或衝突時拒絕下結論。
4. 助理路由只使用允許的讀取工具，不因自然語言要求而修改已確認班表。

## 實際介面與主要成果

![六筆班表明細與工時薪資結果，本機實際截圖](images/demo-results-desktop.jpg)

![合成班表圖片與辨識草稿並列，本機實際截圖](images/demo-review-desktop.jpg)

這組合成班表共有六筆：有效工時依序為 7、7.5、7、4、7.5、7 小時，合計 40 小時；每小時 NT$200，預估 NT$8,000；依班次起始日期計算最長連續工作兩天。9 月 3 日跨夜班 22:00–06:00，8 小時扣除 30 分鐘休息後為 7.5 小時。9 月 9 日固定為 09:00–13:00，休息 0 分鐘。

摘要、明細、合成圖片和覆核結果共用[班表 fixture](../frontend/src/demo/schedule-demo.json)。這些數字描述一個示範輸入，不是節省時間、使用人數、準確率或效能成果。Demo 前端展開計算，沒有宣稱實際呼叫後端計算服務；另以[後端一致性測試](../backend/tests/test_demo_fixture.py)核對 domain 計算。

## 五步操作流程

1. **結果 / Results**：展開六筆明細，檢查日期、時間、休息、工時、時薪與金額。
2. **AI 覆核 / Review**：合成圖片與固定草稿並列；9 月 9 日先由缺少結束時間補正為 13:00，再按「模擬確認」。通過格式檢查不代表已人工確認；確認後也不寫入資料庫。
3. **規章 / Policy**：單一有效版本顯示答案、引用、文件與頁碼。衝突情境同時顯示 A 版六日、B 版四日的限制，因無法判定優先版本而拒答。
4. **助理 / Assistant**：固定的「模擬執行軌跡」呈現問題、證據、hybrid 路由與回答。刪除班次的要求被拒絕，沒有執行寫入，班表不變。
5. **實作與驗證 / Implementation & Evidence**：依資料隔離、工具整合、評估方法三組前往可追查的 repo 文件與測試。

往返步驟保留補正、確認與情境選擇；「重新體驗」才統一重設。不提供真實圖片上傳、即時 RAG、開放式聊天或持久化。規章均為合成文件，不冒充公司規章或法律判定。`#demo` 與舊 `#reviewer` 都能進入導覽。

首頁以「開始體驗」及「查看 GitHub」為主入口，帳號登入為次要入口；API 連線狀態屬於正式工作區資訊，不是使用合成 Demo 的必要條件。

## 系統架構與技術

正式系統路徑為 React → FastAPI → 已驗證身分與 domain/services → PostgreSQL。AI 與工具整合不能取代身分、資料隔離或確定性計算。完整流程圖、ERD 與信任邊界見[架構文件](architecture.md)。

| 層次        | 技術                                                           | 用途與實作證據                                                                                                                                                     |
| ----------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 前端        | React、TypeScript、Vite                                        | 響應式工作區與獨立合成 Demo；[dependencies](../frontend/package.json)、[前端測試](../frontend/tests)                                                               |
| 後端        | Python 3.12、FastAPI、Pydantic、SQLAlchemy、psycopg、Alembic   | 輸入驗證、服務分層與 migrations；[dependencies](../pyproject.toml)、[後端程式](../backend/app)                                                                     |
| 工時計算    | datetime、Decimal、時區與有效期費率                            | 跨夜、休息扣除、工時與預估薪資；[analytics](../backend/app/domain/analytics.py)、[測試](../backend/tests/test_schedule_analytics.py)                               |
| AI 班表匯入 | Gemini structured output、schema validation                    | 候選資料先進草稿，人工確認才允許寫入；[imports](../backend/app/services/imports.py)、[測試](../backend/tests/test_import_service.py)                               |
| 規章檢索    | LangChain、pgvector、PDF 文字處理                              | owner-scoped 文件片段、引用及衝突處理；[retrieval](../backend/app/services/retrieval.py)、[設計決策](decisions/0003-owner-scoped-policy-retrieval.md)              |
| 助理協作    | Stateless LangGraph、確定性路由、可選 Gemini fallback          | 依意圖組合班表與規章證據；[assistant](../backend/app/services/assistant.py)、[路由案例](../evals/routing/cases.json)                                               |
| 身分與隔離  | Supabase JWT、PostgreSQL forced RLS                            | 非 owner、無 BYPASSRLS runtime role；[角色決策](decisions/0002-database-roles-and-pooling.md)、[整合測試](../backend/tests/integration/test_migrations_and_rls.py) |
| Calendar    | OAuth PKCE、最小 scope、加密 refresh token、冪等 event ID、ICS | 同步失敗保留班表真實資料；[設計決策](decisions/0004-calendar-oauth-and-idempotency.md)、[測試](../backend/tests/test_calendar_service.py)                          |
| MCP         | 已驗證、owner-scoped、唯讀工具                                 | 六個工具，不接受任意 owner ID 或 raw SQL；[文件](mcp.md)、[測試](../backend/tests/test_mcp_server.py)                                                              |
| 部署        | Docker、GitHub Actions、GCP Cloud Run、WIF                     | branch-restricted 身分聯邦與受限資源配置；[部署文件](deployment.md)、[release workflow](../.github/workflows/release.yml)                                          |
| 品質        | Vitest、Testing Library、pytest、Ruff、mypy、ESLint、Prettier  | 型別、格式、互動、服務與安全邊界測試；[CI](../.github/workflows/validate.yml)                                                                                      |

## 關鍵設計決策

- **模型輸出與事實分開**：AI 可以解析候選內容，不能成為薪資計算、SQL、身分或已確認班次的真實來源。
- **草稿與確認分開**：格式正確只是必要條件，不等於使用者已同意寫入。
- **引用與拒答並重**：可追溯證據是回答條件。Demo 的固定拒答案例與離線評估中的歷史失敗分開呈現。
- **資料庫強制隔離**：owner scope 不只依靠前端或提示詞，還由 RLS 與受限角色執行。
- **外部整合可以失敗**：Calendar 冪等與可重試狀態、ICS 匯出及安全錯誤碼，避免外部服務失敗改變已確認班表。
- **展示與正式工作區分開**：免登入體驗只用合成素材，既有認證與 CRUD 不變，不開放匿名正式寫入。

## 評估方法、結果與已知失敗

[完整報告](../evals/reports/summary.md)由 `python evals/run.py` 從版本化合成 fixtures 重建，不連網、不使用正式資料庫、不呼叫 live model。本次未修改既有評估案例或數字。

| 評估    | 樣本與方式                                              | 結果                                                                         | 失敗與限制                                                                                                 |
| ------- | ------------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| OCR     | 9 個合成結構化輸出案例，依位置比較欄位                  | 日期 exact match 0.889、時間 0.778、review recall 0.80；3 例失敗             | skewed 時間錯誤；multiple-dates 漏班；illegible 漏標覆核。不是實際圖片解碼品質測試；排序不同也會影響配對。 |
| RAG     | 5 個合成檢索與回答案例，groundedness 使用版本化人工標籤 | Recall@k 0.90、引用正確性 1.00、groundedness 0.80、拒答正確率 0.80；1 例失敗 | conflicting-overtime 發生檢索遺漏、無依據回答、拒答錯誤。片段不涵蓋所有 PDF；fixture 延遲不是即時效能。    |
| Routing | 12 個合成問題，預期意圖與確定性路由比較                 | accuracy 與 deterministic coverage 均為 0.833；2 次 ambiguous 回退           | terse-leave、terse-week 未正確分流；未測量可選 Gemini fallback 準確率。                                    |

這些是小樣本、可重現的方向性證據，不是普遍準確率或正式流量統計。失敗注入測試涵蓋 Gemini 不可用、JWT 金鑰查詢失敗及 Calendar 不可用，但不能推導供應商 SLA。

## 已知限制與本機啟動

- 薪資僅為預估；系統不是正式薪資、法律、人資或就業決策工具。
- Live Demo 是固定流程，不證明所有真實圖片、文件與問題都能正確處理。
- 真實 Gemini、Supabase、Calendar 整合需配置憑證；本次不執行正式資料寫入或線上整合測試。
- 目前 process-local rate limiting 對應單一 instance 配置；水平擴展需 shared limiter。
- 免費額度、成本與外部可用性不是此專案能保證的成果。

純前端體驗需 Node.js 24、pnpm 11.19：

```bash
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend dev --host 127.0.0.1
```

開啟 Vite 顯示的本機網址並加上 `/#demo`。完整系統另需 Python 3.12 與 Docker；設定與驗證命令見 [README](../README.md#run-locally-and-explore-further)、[環境範例](../.env.example)及[部署文件](deployment.md)。

## 進一步閱讀

[使用導覽](demo-script.md) · [API 範例](api-examples.md) · [MCP 文件](mcp.md) · [資料庫整合測試設定](../migrations/README.md) · [合成資料政策](synthetic-data-policy.md)
