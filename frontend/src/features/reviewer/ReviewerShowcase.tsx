import { type ReactNode, useState } from 'react'

import { reviewerLinks, reviewerShowcase } from '../../demo/reviewerShowcase'

type ReviewerShowcaseProps = {
  onExit: () => void
}

const steps = [
  { number: '01', short: '班表', title: '先看結果，再理解計算邊界' },
  { number: '02', short: 'AI 覆核', title: 'AI 只建立草稿，人類決定是否寫入' },
  { number: '03', short: 'RAG', title: '回答必須帶著可追溯的頁面引用' },
  { number: '04', short: '助理', title: 'LangGraph 先路由，再驗證可用證據' },
  {
    number: '05',
    short: '系統證據',
    title: '把安全、整合與部署放在同一條證據鏈',
  },
] as const

export function ReviewerShowcase({ onExit }: ReviewerShowcaseProps) {
  const [index, setIndex] = useState(0)
  const step = steps[index] ?? steps[0]
  const isLast = index === steps.length - 1

  function next() {
    setIndex((current) => Math.min(current + 1, steps.length - 1))
  }

  function previous() {
    setIndex((current) => Math.max(current - 1, 0))
  }

  function replay() {
    setIndex(0)
  }

  return (
    <main className="reviewer-shell">
      <header className="reviewer-header">
        <a className="reviewer-brand" href="#reviewer" onClick={replay}>
          <span>ShiftMate Web</span>
          <strong>Reviewer Showcase</strong>
        </a>
        <div className="reviewer-header__actions">
          <span>唯讀合成結果 · 無外部呼叫</span>
          <button onClick={onExit} type="button">
            返回產品首頁
          </button>
        </div>
      </header>

      <nav aria-label="Reviewer 導覽進度" className="reviewer-progress">
        {steps.map((item, stepIndex) => (
          <button
            aria-label={`${item.number} ${item.short}`}
            aria-current={stepIndex === index ? 'step' : undefined}
            key={item.number}
            onClick={() => setIndex(stepIndex)}
            type="button"
          >
            <span>{item.number}</span>
            {item.short}
          </button>
        ))}
      </nav>

      <section className="reviewer-stage" aria-labelledby="reviewer-title">
        <div className="reviewer-intro">
          <p className="reviewer-kicker">
            CASE {step.number} / {String(steps.length).padStart(2, '0')}
          </p>
          <h1 id="reviewer-title">{step.title}</h1>
          <p>
            每一幕同時說明「使用者看到什麼」、「工程如何做到」，以及系統刻意不做什麼。
          </p>
        </div>

        <div className="reviewer-evidence" key={step.number}>
          {index === 0 && <DashboardCase />}
          {index === 1 && <ImportCase />}
          {index === 2 && <RagCase />}
          {index === 3 && <AssistantCase />}
          {index === 4 && <PlatformCase />}
        </div>
      </section>

      <footer className="reviewer-controls">
        <div>
          <button disabled={index === 0} onClick={previous} type="button">
            上一步
          </button>
          {!isLast && (
            <button className="reviewer-primary" onClick={next} type="button">
              下一步
            </button>
          )}
          {isLast && (
            <button className="reviewer-primary" onClick={replay} type="button">
              重新導覽
            </button>
          )}
        </div>
        <p aria-live="polite">
          第 {index + 1} 步，共 {steps.length} 步
        </p>
      </footer>
    </main>
  )
}

function EvidenceLabel({ children }: { children: ReactNode }) {
  return <p className="reviewer-label">{children}</p>
}

function DashboardCase() {
  const data = reviewerShowcase.dashboard
  return (
    <div className="reviewer-case reviewer-case--dashboard">
      <div className="reviewer-metrics">
        {data.metrics.map((metric) => (
          <article key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>{metric.note}</small>
          </article>
        ))}
      </div>
      <article className="reviewer-detail">
        <EvidenceLabel>跨夜班 edge case</EvidenceLabel>
        <strong>{data.overnight}</strong>
        <p>
          時區、休息時間、跨日與有效期費率都由 deterministic domain service
          計算；LLM 不計薪、不執行 SQL。
        </p>
      </article>
    </div>
  )
}

function ImportCase() {
  const data = reviewerShowcase.importReview
  return (
    <div className="reviewer-case reviewer-case--import">
      <ol className="reviewer-pipeline" aria-label="智慧匯入安全流程">
        {data.pipeline.map((stage) => (
          <li key={stage}>{stage}</li>
        ))}
      </ol>
      <div className="reviewer-candidates">
        {data.candidates.map((candidate) => (
          <article key={`${candidate.date}:${candidate.time}`}>
            <div>
              <strong>{candidate.date}</strong>
              <span>{candidate.time}</span>
            </div>
            <span data-status={candidate.status}>
              {candidate.status === 'confirmed' ? '已確認' : '需要覆核'}
            </span>
            {candidate.warning && <p>{candidate.warning}</p>}
          </article>
        ))}
      </div>
      <p className="reviewer-boundary">
        Schema
        validation、資料庫草稿與逐筆確認，讓模型輸出永遠不會直接成為已確認班次。
      </p>
    </div>
  )
}

function RagCase() {
  const data = reviewerShowcase.rag
  return (
    <div className="reviewer-case reviewer-case--rag">
      <article className="reviewer-answer">
        <EvidenceLabel>合成問題</EvidenceLabel>
        <h2>{data.question}</h2>
        <p>{data.answer}</p>
        <blockquote>
          <strong>{data.citation}</strong>
          <span>「{data.excerpt}」</span>
        </blockquote>
      </article>
      <article className="reviewer-refusal">
        <EvidenceLabel>拒答也是功能</EvidenceLabel>
        <p>{data.refusal}</p>
        <span>RAG evaluation · Recall@k 0.90 · citation correctness 1.00</span>
      </article>
    </div>
  )
}

function AssistantCase() {
  const data = reviewerShowcase.assistant
  return (
    <div className="reviewer-case reviewer-case--assistant">
      <article className="reviewer-answer">
        <EvidenceLabel>問 ShiftMate</EvidenceLabel>
        <h2>{data.question}</h2>
        <div className="reviewer-route">
          <span>{data.route}</span>
          <strong>已驗證證據</strong>
        </div>
        <p>{data.answer}</p>
        <ul className="reviewer-facts" aria-label="deterministic 班表事實">
          {data.facts.map((fact) => (
            <li key={fact}>{fact}</li>
          ))}
        </ul>
      </article>
      <aside className="reviewer-tools">
        <EvidenceLabel>執行軌跡</EvidenceLabel>
        {data.tools.map((tool) => (
          <span key={tool}>{tool}</span>
        ))}
        <p>Stateless · owner-scoped · 無寫入工具</p>
      </aside>
    </div>
  )
}

function PlatformCase() {
  const data = reviewerShowcase.platform
  return (
    <div className="reviewer-case reviewer-case--platform">
      <div className="reviewer-proof-list">
        {data.evidence.map((item) => (
          <article key={item.label}>
            <strong>{item.label}</strong>
            <span>{item.value}</span>
          </article>
        ))}
      </div>
      <aside className="reviewer-release">
        <EvidenceLabel>可追溯成果</EvidenceLabel>
        <h2>不是只挑成功案例</h2>
        <p>
          Repository 同時保留測試、失敗案例、限制、部署政策與 teardown
          步驟，讓每項履歷技術都有可查證證據。
        </p>
        <div>
          <a href={reviewerLinks.repository}>GitHub repository</a>
          <a href={reviewerLinks.openApi}>OpenAPI</a>
          <a href={reviewerLinks.evaluations}>Evaluation reports</a>
          <a href={reviewerLinks.video}>2–3 分鐘影片</a>
        </div>
      </aside>
    </div>
  )
}
