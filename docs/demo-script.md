# Interactive demo guide

This guide uses only the public, versioned, synthetic interactive demo. It
requires no login, test credential, production database query, Gemini call, or
Google Calendar authorization.

## Three-minute live review

Open <https://shiftmate-web-fucvnupudq-de.a.run.app/#demo>.

1. **Problem and deterministic result (30 seconds).** Point out the overnight
   shift, 40-hour total, effective-dated pay estimate, and longest consecutive
   work period. Explain that an LLM does not calculate these values.
2. **AI import with human review (35 seconds).** Follow the pipeline from a
   synthetic schedule image to structured candidates. The incomplete time is
   visibly blocked; only a valid, explicitly confirmed row can become a shift.
3. **Grounded policy answer (30 seconds).** Show the page citation and the
   deliberately visible conflict refusal. A refusal is a successful safety
   outcome, not hidden evaluation noise.
4. **Hybrid assistant (35 seconds).** Show the LangGraph route, used tools,
   deterministic facts, and policy evidence. This is assistance, not a legal,
   HR, or payroll decision.
5. **System evidence (35 seconds).** Connect RLS, read-only MCP, Calendar sync
   with ICS fallback, WIF deployment, bounded Cloud Run, CI, and offline
   evaluation. Finish with the repository, OpenAPI, and evaluation links.

## 150-second video storyboard and narration source

| Time | Scene | Mandarin narration | English secondary subtitle |
| --- | --- | --- | --- |
| 00:00–00:25 | Problem and result | 排班工具真正困難的，不只是把班次放進日曆，而是讓工時、薪資估算與跨夜班都能被驗證。ShiftMate 將這些計算留給確定性的程式，語言模型不計薪，也不執行 SQL。 | Reliable schedules require verifiable hours, pay estimates, and overnight handling. Deterministic code owns the calculation boundary. |
| 00:25–00:52 | AI review | 班表影像先由 Gemini 轉成結構化候選資料，但模型輸出只會進入草稿。格式檢查會標記不完整或不合法的列，使用者逐筆確認後，才允許寫入正式班表。 | Gemini proposes structured candidates. Validation and explicit human confirmation guard every confirmed write. |
| 00:52–01:22 | RAG and assistant | 問到工作規章時，系統只使用所屬使用者的文件片段，答案附上文件與頁碼。相關度不足或規則衝突時，系統拒絕判定。LangGraph 先路由問題，再合併確定性的班表事實與可追溯的規章證據。 | Owner-scoped RAG returns page citations and refuses weak or conflicting evidence. LangGraph combines facts with grounded policy. |
| 01:22–01:54 | Safety and cloud | 每次資料庫請求都受 Row Level Security 隔離。MCP 只提供六個唯讀工具。Google Calendar 採最小權限與冪等同步，失敗時仍可匯出 ICS。GitHub 透過 WIF 部署到受限的 Cloud Run，不使用服務帳號金鑰。 | RLS, read-only MCP, least-privilege Calendar access, ICS fallback, WIF, and bounded Cloud Run form one evidence chain. |
| 01:54–02:30 | Limits and CTA | 評估不只展示成功案例：OCR 九例有三個失敗，RAG 五例有一個衝突失敗，路由十二例有兩個保守回退。這些都是合成、可重跑的方向性證據，不代表正式人資或法律系統。請從互動 Demo、原始碼與 OpenAPI 檢查完整取捨。 | Failures stay visible. Synthetic offline evaluations are directional evidence—not production HR or legal readiness. Review the trade-offs in code. |

The versioned HyperFrames composition, exact subtitle timing source, local TTS
instructions, and render command live under `portfolio/video/`.
