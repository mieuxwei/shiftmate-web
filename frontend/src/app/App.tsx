import { useEffect, useState } from 'react'

import { getHealth, type HealthStatus } from '../api/health'
import './app.css'

type ConnectionState =
  | { kind: 'loading' }
  | { kind: 'ready'; health: HealthStatus }
  | { kind: 'error' }

export function App() {
  const [connection, setConnection] = useState<ConnectionState>({
    kind: 'loading',
  })

  useEffect(() => {
    const controller = new AbortController()

    void getHealth(controller.signal)
      .then((health) => setConnection({ kind: 'ready', health }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setConnection({ kind: 'error' })
      })

    return () => controller.abort()
  }, [])

  return (
    <main>
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">ShiftMate Web</p>
        <h1 id="page-title">你的班表，清楚而安心。</h1>
        <p className="lede">
          這是使用合成資料的開發展示環境。排班、匯入與助理功能會在後續里程碑逐步開放。
        </p>

        <div className={`status status--${connection.kind}`} role="status">
          <span className="status__dot" aria-hidden="true" />
          {connection.kind === 'loading' && '正在連接 API…'}
          {connection.kind === 'ready' &&
            `API 已連線 · ${connection.health.environment}`}
          {connection.kind === 'error' && 'API 尚未連線'}
        </div>
      </section>

      <section className="preview" aria-label="功能預覽">
        <article>
          <span>01</span>
          <h2>班表</h2>
          <p>集中檢視個人班次與工時。</p>
        </article>
        <article>
          <span>02</span>
          <h2>智慧匯入</h2>
          <p>先檢查、再確認，不讓 AI 直接寫入。</p>
        </article>
        <article>
          <span>03</span>
          <h2>規章助理</h2>
          <p>以引用來源回答合成政策問題。</p>
        </article>
      </section>
    </main>
  )
}
