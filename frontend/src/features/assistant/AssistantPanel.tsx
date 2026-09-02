import { type FormEvent, useState } from 'react'

import type { ApiClient } from '../../api/client'
import type {
  AssistantAnswer,
  AssistantIntent,
  AssistantToolTrace,
  DateRange,
} from '../../api/types'

export type AssistantClient = Pick<ApiClient, 'queryAssistant'>

const intentLabels: Record<AssistantIntent, string> = {
  schedule: '班表分析',
  policy: '規章查詢',
  hybrid: '班表 × 規章',
  unsupported: '不支援',
}

const toolLabels: Record<AssistantToolTrace['name'], string> = {
  schedule_summary: '班表摘要',
  policy_retrieval: '規章檢索',
  rule_evaluator: '規則比對',
}

type Exchange = {
  question: string
  response: AssistantAnswer
}

export function AssistantPanel({
  client,
  range,
}: {
  client: AssistantClient
  range: DateRange
}) {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<Exchange[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const submitted = question.trim()
    if (!submitted) return
    setBusy(true)
    setMessage(null)
    try {
      const response = await client.queryAssistant(submitted, range)
      setHistory((current) => [...current, { question: submitted, response }])
      setQuestion('')
    } catch {
      setMessage('助理目前無法完成查詢；班表與儀表板仍可使用。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section
      className="manager assistant-panel"
      aria-labelledby="assistant-title"
    >
      <div className="section-heading">
        <div>
          <p className="section-kicker">Stateless LangGraph assistant</p>
          <h2 id="assistant-title">班表與規章助理</h2>
        </div>
        <p>
          分析期間 {range.dateFrom} – {range.dateTo}
        </p>
      </div>

      <p className="assistant-disclaimer">
        這是作品示範，不構成法律、人資或薪資建議。工時與預估薪資由程式計算，AI
        不會執行 SQL 或修改班表。
      </p>

      <div className="assistant-history" aria-live="polite">
        {history.length === 0 && (
          <p className="assistant-empty">
            可詢問這段期間的工時、預估薪資、規章內容，或比較班表與連續工作規定。
          </p>
        )}
        {history.map((exchange, index) => (
          <article
            className="assistant-exchange"
            key={`${index}:${exchange.question}`}
          >
            <p className="assistant-question">{exchange.question}</p>
            <div className="assistant-answer">
              <header>
                <strong>{intentLabels[exchange.response.intent]}</strong>
                <span>
                  {exchange.response.refused ? '資料不足' : '已驗證證據'}
                </span>
              </header>
              <p>{exchange.response.answer}</p>
              {exchange.response.schedule_facts && (
                <dl className="assistant-facts" aria-label="班表事實">
                  <div>
                    <dt>班數</dt>
                    <dd>{exchange.response.schedule_facts.shift_count}</dd>
                  </div>
                  <div>
                    <dt>總工時</dt>
                    <dd>
                      {exchange.response.schedule_facts.total_paid_hours} 小時
                    </dd>
                  </div>
                  <div>
                    <dt>預估薪資</dt>
                    <dd>
                      {exchange.response.schedule_facts.currency}{' '}
                      {exchange.response.schedule_facts.estimated_pay}
                    </dd>
                  </div>
                  <div>
                    <dt>最長連續工作</dt>
                    <dd>
                      {
                        exchange.response.schedule_facts
                          .longest_consecutive_days
                      }{' '}
                      天
                    </dd>
                  </div>
                </dl>
              )}
              {exchange.response.tools.length > 0 && (
                <ul className="assistant-tools" aria-label="使用的工具">
                  {exchange.response.tools.map((tool) => (
                    <li key={tool.name} data-status={tool.status}>
                      {toolLabels[tool.name]} ·{' '}
                      {tool.status === 'used' ? '已使用' : '資料不足'}
                    </li>
                  ))}
                </ul>
              )}
              {exchange.response.citations.length > 0 && (
                <ol className="assistant-citations" aria-label="引用來源">
                  {exchange.response.citations.map((citation) => (
                    <li key={citation.chunk_id}>
                      <strong>
                        {citation.title}，第 {citation.page_number} 頁
                      </strong>
                      <blockquote>{citation.excerpt}</blockquote>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </article>
        ))}
      </div>

      <form
        className="assistant-form"
        onSubmit={(event) => {
          void submit(event)
        }}
      >
        <label>
          問 ShiftMate
          <textarea
            maxLength={1000}
            minLength={2}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="例如：我的班表有違反連續工作規定嗎？"
            required
            value={question}
          />
        </label>
        <button className="primary-action" disabled={busy} type="submit">
          {busy ? '分析中…' : '送出問題'}
        </button>
      </form>
      {message && (
        <p className="policy-message" role="status">
          {message}
        </p>
      )}
    </section>
  )
}
