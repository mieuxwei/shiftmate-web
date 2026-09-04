import { useEffect, useRef, useState } from 'react'
import {
  demoShifts,
  demoTotals,
  money,
  policySources,
  repoFile,
  reviewerLinks,
  scheduleImage,
} from '../../demo/reviewerShowcase'

const steps = [
  {
    short: '結果',
    title: '班表與收入 / Results',
    hint: '從六筆班次重算工時與預估收入。',
  },
  {
    short: 'AI 覆核',
    title: 'AI 提案，人類確認 / Review',
    hint: '比對合成圖片，先補正，再模擬人工確認。',
  },
  {
    short: '規章',
    title: '答案回到原文 / Policy',
    hint: '切換有效版本與衝突版本，檢查回答依據。',
  },
  {
    short: '助理',
    title: '班表 × 規章 / Assistant',
    hint: '從問題、證據與路由，看清楚回答的安全邊界。',
  },
  {
    short: '證據',
    title: '實作與驗證 / Implementation & Evidence',
    hint: '區分系統實作、合成示範與離線評估。',
  },
] as const

export function ReviewerShowcase({ onExit }: { onExit: () => void }) {
  const [index, setIndex] = useState(0)
  const [review, setReview] = useState<'pending' | 'validated' | 'confirmed'>(
    'pending',
  )
  const [conflict, setConflict] = useState(false)
  const [writeRequest, setWriteRequest] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const title = useRef<HTMLHeadingElement>(null)
  const confirmation = useRef<HTMLButtonElement>(null)
  const reviewStatus = useRef<HTMLParagraphElement>(null)
  const step = steps[index]!
  useEffect(() => {
    title.current?.focus({ preventScroll: true })
    title.current?.scrollIntoView?.({ block: 'nearest' })
  }, [index])
  useEffect(() => {
    if (review === 'validated') confirmation.current?.focus()
    if (review === 'confirmed') reviewStatus.current?.focus()
  }, [review])
  function replay() {
    setReview('pending')
    setConflict(false)
    setWriteRequest(false)
    setExpanded(false)
    setIndex(0)
    title.current?.focus({ preventScroll: true })
  }
  return (
    <main className="reviewer-shell">
      <header className="reviewer-header">
        <a className="reviewer-brand" href="#demo" onClick={() => setIndex(0)}>
          <span>ShiftMate Web</span>
          <strong>Interactive Demo</strong>
        </a>
        <div className="reviewer-header__actions">
          <span>2 分鐘自助體驗 · 唯讀合成資料</span>
          <button onClick={onExit} type="button">
            返回首頁
          </button>
        </div>
      </header>
      {index === 0 && (
        <aside className="reviewer-scenario" aria-label="Demo 情境">
          <span>Scenario</span>
          <p>
            輪班工作者 Mia 要核對 2026 年 9
            月的班表、跨夜工時與預估收入，再查閱連續工作規則。以下為免登入、前端固定合成情境；不呼叫
            AI、Calendar 或正式班表 API，不寫入資料庫。
          </p>
        </aside>
      )}
      <nav aria-label="Demo 導覽進度" className="reviewer-progress">
        {steps.map((item, i) => (
          <button
            key={item.short}
            type="button"
            aria-current={index === i ? 'step' : undefined}
            aria-label={String(i + 1).padStart(2, '0') + ' ' + item.short}
            onClick={() => setIndex(i)}
          >
            <span>{String(i + 1).padStart(2, '0')}</span>
            {item.short}
          </button>
        ))}
      </nav>
      <section className="reviewer-stage" aria-labelledby="demo-title">
        <div className="reviewer-intro">
          <p className="reviewer-kicker">
            {String(index + 1).padStart(2, '0')} / 05
          </p>
          <h1 id="demo-title" ref={title} tabIndex={-1}>
            {step.title}
          </h1>
          <p>{step.hint}</p>
        </div>
        <div className="reviewer-evidence">
          {index === 0 && (
            <div className="reviewer-case">
              <div className="reviewer-metrics">
                {[
                  {
                    label: '總工時',
                    value: String(demoTotals.hours),
                    note: '小時',
                  },
                  {
                    label: '預估薪資',
                    value: money(demoTotals.amount),
                    note: '時薪 NT$200',
                  },
                  {
                    label: '班次',
                    value: String(demoTotals.count),
                    note: '筆合成資料',
                  },
                  {
                    label: '最長連續工作',
                    value: String(demoTotals.longest),
                    note: '天 · 依班次起始日期',
                  },
                ].map((metric) => (
                  <article key={metric.label}>
                    <span>{metric.label}</span>
                    <strong>{metric.value}</strong>
                    <small>{metric.note}</small>
                  </article>
                ))}
              </div>
              <article className="reviewer-detail">
                <span className="reviewer-label">跨夜與休息 / Overnight</span>
                <h2>22:00–06:00 → 7.5 小時</h2>
                <p>
                  9 月 3 日 22:00 至翌日 06:00：8 小時 − 0.5 小時休息 = 7.5
                  小時。
                </p>
                <p>
                  合計 {demoTotals.hours} × 200 = {money(demoTotals.amount)}
                  。此處由前端合成 fixture 展開計算，不代表呼叫了後端計算服務。
                </p>
              </article>
              <details
                className="reviewer-detail reviewer-ledger"
                open={expanded}
                onToggle={(event) => setExpanded(event.currentTarget.open)}
              >
                <summary>展開六筆班表明細 / Shift ledger</summary>
                <div
                  className="reviewer-table-scroll"
                  tabIndex={0}
                  role="region"
                  aria-label="六筆班表明細，可橫向捲動"
                >
                  <table>
                    <caption>2026 年 9 月 · Asia/Taipei · 合成資料</caption>
                    <thead>
                      <tr>
                        {[
                          '日期',
                          '起訖時間',
                          '休息扣除',
                          '有效工時',
                          '時薪',
                          '金額',
                        ].map((label) => (
                          <th key={label} scope="col">
                            {label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {demoShifts.map((shift) => (
                        <tr key={shift.date}>
                          <th scope="row">{shift.date.slice(5)}</th>
                          <td>{shift.time}</td>
                          <td>{shift.breakMinutes} 分鐘</td>
                          <td>{shift.paidHours} 小時</td>
                          <td>{money(shift.rate)}</td>
                          <td>{money(shift.amount)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <th scope="row" colSpan={3}>
                          總計
                        </th>
                        <td>{demoTotals.hours} 小時</td>
                        <td>NT$200</td>
                        <td>{money(demoTotals.amount)}</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </details>
            </div>
          )}
          {index === 1 && (
            <div className="reviewer-case">
              <p className="reviewer-boundary">
                固定合成素材與辨識草稿示範；沒有上傳、模型推論或資料庫操作。實際系統以格式驗證與人工覆核守住寫入邊界。
              </p>
              <div className="reviewer-review-grid">
                <figure>
                  <img
                    src={scheduleImage}
                    alt="合成班表圖片：2026 年 9 月六筆班次，9 月 9 日為 09:00–13:00；完整內容與結果明細一致。"
                  />
                  <figcaption>合成班表圖片 / Synthetic input</figcaption>
                </figure>
                <article className="reviewer-detail">
                  <h2>辨識草稿 / Draft</h2>
                  <ul className="reviewer-draft">
                    {demoShifts.map((shift) => (
                      <li key={shift.date}>
                        <span>{shift.date.slice(5)}</span>
                        <strong>
                          {shift.date === '2026-09-09' && review === 'pending'
                            ? '09:00–?'
                            : shift.time}
                        </strong>
                      </li>
                    ))}
                  </ul>
                  <p>
                    9 月 9 日：
                    {review === 'pending'
                      ? '結束時間不清楚，禁止直接寫入'
                      : '09:00–13:00 · 休息 0 分鐘 · 4 小時'}
                  </p>
                </article>
              </div>
              <ol className="reviewer-review-states" aria-label="覆核流程">
                <li aria-current={review === 'pending' ? 'step' : undefined}>
                  待覆核
                </li>
                <li aria-current={review === 'validated' ? 'step' : undefined}>
                  通過格式檢查
                </li>
                <li aria-current={review === 'confirmed' ? 'step' : undefined}>
                  人工確認
                </li>
              </ol>
              <div className="reviewer-choice reviewer-choice--row">
                <button
                  type="button"
                  disabled={review !== 'pending'}
                  onClick={() => setReview('validated')}
                >
                  模擬補正為 13:00
                </button>
                <button
                  type="button"
                  disabled={review !== 'validated'}
                  ref={confirmation}
                  onClick={() => setReview('confirmed')}
                >
                  模擬確認
                </button>
              </div>
              <p role="status" ref={reviewStatus} tabIndex={-1}>
                {review === 'pending'
                  ? '待覆核：先比對圖片並補正結束時間。'
                  : review === 'validated'
                    ? '通過格式檢查，尚未人工確認。'
                    : '已確認，僅本次示範，不寫入資料庫'}
              </p>
            </div>
          )}
          {index === 2 && (
            <div className="reviewer-case">
              <div className="reviewer-choice reviewer-choice--row">
                <button
                  type="button"
                  aria-pressed={!conflict}
                  onClick={() => setConflict(false)}
                >
                  單一有效版本
                </button>
                <button
                  type="button"
                  aria-pressed={conflict}
                  onClick={() => setConflict(true)}
                >
                  衝突版本
                </button>
              </div>
              <article className="reviewer-detail">
                <h2>連續工作最多可以幾天？</h2>
                <p>
                  以下均為合成文件與固定回答，不是真實公司規章或即時檢索結果。
                </p>
                <p role="status">
                  {conflict
                    ? '兩份同期間文件分別規定六日與四日，且無法判定優先版本：拒絕回答，未提供合規判定。'
                    : '依合成員工手冊 A，連續工作不得超過六日；例外安排須人工覆核。'}
                </p>
              </article>
              <div className="reviewer-policy-sources">
                {policySources.slice(0, conflict ? 2 : 1).map((source) => (
                  <article className="reviewer-detail" key={source.version}>
                    <span className="reviewer-label">{source.version}</span>
                    <h2>{source.name}</h2>
                    <blockquote>{source.excerpt}</blockquote>
                    <p>出處：{source.source}</p>
                  </article>
                ))}
              </div>
            </div>
          )}
          {index === 3 && (
            <div className="reviewer-case">
              <div className="reviewer-choice reviewer-choice--row">
                <button
                  type="button"
                  aria-pressed={!writeRequest}
                  onClick={() => setWriteRequest(false)}
                >
                  班表 × 規章
                </button>
                <button
                  type="button"
                  aria-pressed={writeRequest}
                  onClick={() => setWriteRequest(true)}
                >
                  嘗試寫入要求
                </button>
              </div>
              <article className="reviewer-detail">
                <span className="reviewer-label">
                  合成情境示範 / Fixed scenario
                </span>
                <h2>
                  {writeRequest
                    ? '請幫我刪除 9 月 3 日的夜班。'
                    : '我的班表有違反連續工作規定嗎？'}
                </h2>
                <p>
                  路由：
                  {writeRequest
                    ? 'unsupported · 寫入要求'
                    : 'hybrid · 班表 × 規章'}
                </p>
                <p>
                  {writeRequest
                    ? '證據：要求刪除已確認班次，超出唯讀工具能力，不讀取或修改班表。'
                    : '證據：六筆合成班表最長連續 2 天；合成員工手冊 A 第 4 頁門檻為六日（使用單一有效版本）。'}
                </p>
              </article>
              <article className="reviewer-detail">
                <h2>模擬執行軌跡</h2>
                <ol>
                  {(writeRequest
                    ? [
                        '意圖路由 → 不支援寫入',
                        '資料工具 → 未呼叫',
                        '寫入操作 → 未執行；班表未變更',
                      ]
                    : [
                        '意圖路由 → hybrid',
                        '班表摘要 → 6 班、40 小時、最長 2 天',
                        '規章證據 → 手冊 A，第 4 頁，六日上限',
                        '規則比對 → 2 ≤ 6',
                      ]
                  ).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ol>
                <p role="status">
                  {writeRequest
                    ? '拒絕寫入：助理只有讀取工具。未執行寫入，班表未變更。'
                    : '合成回答：目前最長連續工作 2 天，未超過此示範規章的六日門檻。不構成法律、人資或薪資判定。'}
                </p>
              </article>
            </div>
          )}
          {index === 4 && (
            <div className="reviewer-case">
              <article className="reviewer-detail">
                <h2>01 · 資料隔離與安全邊界</h2>
                <p>
                  PostgreSQL forced RLS 與無 BYPASSRLS 的 runtime role；AI
                  草稿須經人工確認，助理不提供已確認班次的寫入工具。
                </p>
                <ul>
                  <li>
                    <a
                      href={repoFile(
                        'backend/tests/integration/test_migrations_and_rls.py',
                      )}
                    >
                      RLS 整合測試
                    </a>
                  </li>
                  <li>
                    <a href={repoFile('backend/tests/test_import_service.py')}>
                      草稿與確認測試
                    </a>
                  </li>
                  <li>
                    <a
                      href={repoFile('backend/tests/test_assistant_service.py')}
                    >
                      助理路由與安全測試
                    </a>
                  </li>
                </ul>
              </article>
              <article className="reviewer-detail">
                <h2>02 · 工具整合與失敗處理</h2>
                <p>
                  Calendar 冪等同步、加密 token 與 ICS 匯出；六個 owner-scoped
                  唯讀 MCP 工具。以下是實作與測試證據，不表示此 Demo
                  有呼叫外部服務。
                </p>
                <ul>
                  <li>
                    <a
                      href={repoFile(
                        'docs/decisions/0004-calendar-oauth-and-idempotency.md',
                      )}
                    >
                      Calendar 設計決策
                    </a>{' '}
                    ·{' '}
                    <a
                      href={repoFile('backend/tests/test_calendar_service.py')}
                    >
                      同步失敗與資料不變測試
                    </a>
                  </li>
                  <li>
                    <a href={repoFile('docs/mcp.md')}>
                      MCP transport 與工具文件
                    </a>{' '}
                    ·{' '}
                    <a href={repoFile('backend/tests/test_mcp_server.py')}>
                      工具測試
                    </a>
                  </li>
                  <li>
                    <a href={repoFile('evals/failure_modes/cases.json')}>
                      Gemini、JWT、Calendar 失敗注入案例
                    </a>
                  </li>
                </ul>
              </article>
              <article className="reviewer-detail">
                <h2>03 · 評估方法、結果與限制</h2>
                <p>
                  離線、版本化合成 fixtures；不呼叫 live
                  model。小樣本結果不是普遍準確率，也不是 Demo
                  固定數字的效能評估。
                </p>
                <ul>
                  <li>
                    OCR：9 例、3 個失敗；日期 exact match 0.889、時間
                    0.778、覆核召回
                    0.80。比較結構化輸出，不測實際圖片解碼；skewed
                    時間錯誤、multiple-dates 漏班、illegible 漏標覆核。
                  </li>
                  <li>
                    RAG：5 例、1 個失敗；Recall@k 0.90、引用正確性
                    1.00、groundedness 0.80、拒答正確率 0.80。合成片段與人工
                    groundedness 標籤；conflicting-overtime
                    有檢索遺漏、無依據回答與拒答錯誤。fixture 延遲不是即時效能。
                  </li>
                  <li>
                    Routing：12 題、2 個 ambiguous 回退；accuracy
                    0.833、deterministic coverage 0.833。terse-leave 與
                    terse-week 未正確分流；未評估可選 Gemini fallback。
                  </li>
                </ul>
                <p>
                  <a href={reviewerLinks.evaluations}>完整評估報告與失敗案例</a>{' '}
                  · <a href={repoFile('evals/run.py')}>重現評估方法</a> ·{' '}
                  <a href={repoFile('backend/tests/test_demo_fixture.py')}>
                    合成班表與後端計算一致性測試
                  </a>
                </p>
              </article>
              <div className="reviewer-release">
                <p>查看實作，或重新檢查這組合成資料。</p>
                <div>
                  <a href={reviewerLinks.repository}>GitHub</a>
                  <a href={reviewerLinks.evaluations}>評估報告</a>
                  <button
                    type="button"
                    className="reviewer-inline-action"
                    onClick={replay}
                  >
                    重新體驗
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
      <footer className="reviewer-controls">
        <div>
          <button
            type="button"
            disabled={index === 0}
            onClick={() => setIndex(index - 1)}
          >
            上一步
          </button>
          {index < 4 && (
            <button
              type="button"
              className="reviewer-primary"
              onClick={() => setIndex(index + 1)}
            >
              下一步
            </button>
          )}
        </div>
        <p aria-live="polite">
          第 {index + 1} 步，共 5 步 · 狀態僅保留於本次體驗
        </p>
      </footer>
    </main>
  )
}
