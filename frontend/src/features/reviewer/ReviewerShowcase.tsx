import { type ReactNode, useState } from 'react'

import { reviewerLinks, reviewerShowcase } from '../../demo/reviewerShowcase'

type ReviewerShowcaseProps = {
  onExit: () => void
}

const steps = [
  {
    number: '01',
    short: '結果',
    title: '先確認班表與收入是否正確',
    story: 'Mia 想快速核對跨夜班、休息時間與這個月的預估收入。',
    outcome: '一眼看懂 6 筆班次、40 小時與 NT$8,000 預估薪資。',
    proof: '時區、跨日與費率都能由相同輸入重算。',
  },
  {
    number: '02',
    short: 'AI 覆核',
    title: 'AI 提案，人類確認',
    story: 'Mia 上傳合成班表後，先處理一筆結束時間不清楚的候選資料。',
    outcome: '修正前不能確認，修正後才進入可寫入狀態。',
    proof: 'Schema validation、草稿與逐筆確認分開。',
  },
  {
    number: '03',
    short: '規章',
    title: '答案必須能回到原文',
    story: 'Mia 查詢連續工作限制，也測試文件版本互相衝突時的結果。',
    outcome: '可回答時顯示文件與頁碼；衝突時明確拒答。',
    proof: '檢索證據是回答條件，不是裝飾性附件。',
  },
  {
    number: '04',
    short: '助理',
    title: '把班表事實與規章證據放在一起',
    story: 'Mia 想知道自己的排班是否接近規章門檻，並嘗試要求助理修改資料。',
    outcome: '讀取型問題有來源；寫入要求被拒絕。',
    proof: 'LangGraph 路由後只呼叫允許的 owner-scoped 工具。',
  },
  {
    number: '05',
    short: '證據',
    title: '驗證它如何在安全邊界內運作',
    story: '最後離開產品畫面，檢查資料隔離、整合、部署與測試證據。',
    outcome: '每項履歷技術都有可追查的程式碼或報告。',
    proof: 'Repository、OpenAPI、evaluation 與影片互相對得上。',
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
        <a className="reviewer-brand" href="#demo" onClick={replay}>
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

      <aside className="reviewer-scenario" aria-label="Demo 情境">
        <span>Scenario</span>
        <p>
          輪班工作者 Mia
          收到一張班表截圖。她要確認班次、預估收入，並查清楚連續工作規則；整條流程不需帳號，也不會寫入資料庫。
        </p>
      </aside>

      <nav aria-label="Demo 導覽進度" className="reviewer-progress">
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
          <p>{step.story}</p>
          <dl className="reviewer-takeaways">
            <div>
              <dt>使用者完成</dt>
              <dd>{step.outcome}</dd>
            </div>
            <div>
              <dt>可驗證證據</dt>
              <dd>{step.proof}</dd>
            </div>
          </dl>
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
  const [corrected, setCorrected] = useState(false)
  return (
    <div className="reviewer-case reviewer-case--import">
      <ol className="reviewer-pipeline" aria-label="智慧匯入安全流程">
        {data.pipeline.map((stage) => (
          <li key={stage}>{stage}</li>
        ))}
      </ol>
      <div className="reviewer-candidates">
        {data.candidates.map((candidate) => {
          const isCorrected = candidate.status === 'review' && corrected
          return (
            <article key={`${candidate.date}:${candidate.time}`}>
              <div>
                <strong>{candidate.date}</strong>
                <span>{isCorrected ? '09:00–17:00' : candidate.time}</span>
              </div>
              <span data-status={isCorrected ? 'ready' : candidate.status}>
                {candidate.status === 'confirmed'
                  ? '已確認'
                  : isCorrected
                    ? '可確認'
                    : '需要覆核'}
              </span>
              {candidate.warning && !isCorrected && <p>{candidate.warning}</p>}
            </article>
          )
        })}
      </div>
      <div className="reviewer-try">
        <div>
          <EvidenceLabel>Try it</EvidenceLabel>
          <p role="status">
            {corrected
              ? '結束時間已補正；資料通過驗證，但仍需人工確認才會寫入。'
              : '目前有 1 筆資料被阻擋，不能直接寫入班表。'}
          </p>
        </div>
        <button
          aria-pressed={corrected}
          className="reviewer-inline-action"
          onClick={() => setCorrected((value) => !value)}
          type="button"
        >
          {corrected ? '還原不確定欄位' : '模擬人工補正 17:00'}
        </button>
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
  const [showConflict, setShowConflict] = useState(false)
  return (
    <div className="reviewer-case reviewer-case--rag">
      <article className="reviewer-answer">
        <EvidenceLabel>合成問題</EvidenceLabel>
        <h2>{data.question}</h2>
        {!showConflict && (
          <>
            <p>{data.answer}</p>
            <blockquote>
              <strong>{data.citation}</strong>
              <span>「{data.excerpt}」</span>
            </blockquote>
          </>
        )}
        {showConflict && (
          <div className="reviewer-refusal-result" role="status">
            <strong>資料不足，未提供合規判定</strong>
            <p>{data.refusal}</p>
          </div>
        )}
      </article>
      <article className="reviewer-refusal">
        <EvidenceLabel>切換證據狀態</EvidenceLabel>
        <div className="reviewer-choice" aria-label="規章證據狀態">
          <button
            aria-pressed={!showConflict}
            onClick={() => setShowConflict(false)}
            type="button"
          >
            單一有效版本
          </button>
          <button
            aria-pressed={showConflict}
            onClick={() => setShowConflict(true)}
            type="button"
          >
            衝突版本
          </button>
        </div>
        <p>同一個問題會依可用證據回答或拒答，不會同時展示兩種結論。</p>
        <span>RAG evaluation · Recall@k 0.90 · citation correctness 1.00</span>
      </article>
    </div>
  )
}

function AssistantCase() {
  const data = reviewerShowcase.assistant
  const [writeRequest, setWriteRequest] = useState(false)
  return (
    <div className="reviewer-case reviewer-case--assistant">
      <article className="reviewer-answer">
        <EvidenceLabel>問 ShiftMate</EvidenceLabel>
        <div
          className="reviewer-choice reviewer-choice--row"
          aria-label="助理問題"
        >
          <button
            aria-pressed={!writeRequest}
            onClick={() => setWriteRequest(false)}
            type="button"
          >
            班表 × 規章
          </button>
          <button
            aria-pressed={writeRequest}
            onClick={() => setWriteRequest(true)}
            type="button"
          >
            嘗試寫入要求
          </button>
        </div>
        <h2>{writeRequest ? data.writeQuestion : data.question}</h2>
        <div className="reviewer-route">
          <span>
            {writeRequest ? 'unsupported · write request' : data.route}
          </span>
          <strong>{writeRequest ? '安全拒絕' : '已驗證證據'}</strong>
        </div>
        <p>{writeRequest ? data.writeRefusal : data.answer}</p>
        {!writeRequest && (
          <ul className="reviewer-facts" aria-label="deterministic 班表事實">
            {data.facts.map((fact) => (
              <li key={fact}>{fact}</li>
            ))}
          </ul>
        )}
      </article>
      <aside className="reviewer-tools">
        <EvidenceLabel>執行軌跡</EvidenceLabel>
        {(writeRequest ? data.writeTools : data.tools).map((tool) => (
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
