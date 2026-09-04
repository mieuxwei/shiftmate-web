import { type FormEvent, useEffect, useMemo, useState } from 'react'

import { ApiClient, type AccessTokenProvider } from '../api/client'
import { getHealth, type HealthStatus } from '../api/health'
import { configuredAuthGateway, type AuthGateway } from '../auth/session'
import { useAuthSession } from '../auth/useAuthSession'
import { syntheticDemoClient } from '../demo/syntheticDemo'
import { ReviewerShowcase } from '../features/reviewer/ReviewerShowcase'
import {
  Workspace,
  type WorkspaceClient,
} from '../features/workspace/Workspace'
import './app.css'

type ConnectionState =
  | { kind: 'loading' }
  | { kind: 'ready'; health: HealthStatus }
  | { kind: 'error' }

type AppProps = {
  authGateway?: AuthGateway | null
  apiClientFactory?: (getAccessToken: AccessTokenProvider) => WorkspaceClient
}

function defaultApiClientFactory(getAccessToken: AccessTokenProvider) {
  return new ApiClient(getAccessToken)
}

export function App({
  authGateway = configuredAuthGateway,
  apiClientFactory = defaultApiClientFactory,
}: AppProps) {
  const [showPortfolioDemo, setShowPortfolioDemo] = useState(
    () =>
      window.location.hash === '#demo' || window.location.hash === '#reviewer',
  )
  const [connection, setConnection] = useState<ConnectionState>({
    kind: 'loading',
  })
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showDemo, setShowDemo] = useState(false)

  useEffect(() => {
    const syncDemoRoute = () =>
      setShowPortfolioDemo(
        window.location.hash === '#demo' ||
          window.location.hash === '#reviewer',
      )
    window.addEventListener('hashchange', syncDemoRoute)
    return () => window.removeEventListener('hashchange', syncDemoRoute)
  }, [])

  function openPortfolioDemo() {
    window.location.hash = 'demo'
    setShowPortfolioDemo(true)
  }

  function closePortfolioDemo() {
    window.history.replaceState(
      null,
      '',
      `${window.location.pathname}${window.location.search}`,
    )
    setShowPortfolioDemo(false)
  }
  const auth = useAuthSession(authGateway)
  const accessToken =
    auth.state.kind === 'signed-in' ? auth.state.session.accessToken : null
  const apiClient = useMemo(
    () => apiClientFactory(() => accessToken),
    [accessToken, apiClientFactory],
  )

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

  function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const submittedPassword = password
    setPassword('')
    void auth.signIn(email.trim(), submittedPassword)
  }

  if (showPortfolioDemo) return <ReviewerShowcase onExit={closePortfolioDemo} />

  return (
    <main>
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">ShiftMate · Interactive portfolio</p>
        <h1 id="page-title">從班表影像，到可驗證的工時與規章答案。</h1>
        <p className="lede">
          為輪班工作者設計的安全優先助理：AI
          負責提出候選資料，確定性程式負責工時與薪資估算，人類保留最後確認權。
        </p>

        <div className="hero-actions">
          <button
            className="hero-primary"
            onClick={openPortfolioDemo}
            type="button"
          >
            開始體驗
          </button>
          <a href="https://github.com/mieuxwei/shiftmate-web">查看 GitHub</a>
          <span>5 個步驟 · 約 2 分鐘 · 100% 合成資料 · 不需 API 連線</span>
        </div>
        <ul className="hero-proof" aria-label="Demo 特點">
          <li>Human-in-the-loop</li>
          <li>失敗案例可見</li>
          <li>桌機與手機皆可操作</li>
        </ul>
      </section>

      <section className="preview" aria-label="核心產品流程">
        <article>
          <span>01 · Capture</span>
          <h2>班表圖片轉成草稿</h2>
          <p>模型只提出結構化候選資料；格式錯誤與不確定欄位會被攔下。</p>
        </article>
        <article>
          <span>02 · Verify</span>
          <h2>工時與預估薪資可重算</h2>
          <p>跨夜、休息時間、時區與有效期費率都由 domain service 計算。</p>
        </article>
        <article>
          <span>03 · Explain</span>
          <h2>規章回答帶頁碼引用</h2>
          <p>證據不足或版本衝突時明確拒答，不把模型輸出當成判定。</p>
        </article>
      </section>

      <section className="auth" aria-labelledby="auth-title" aria-live="polite">
        <div>
          <p className="auth__kicker">Optional live workspace</p>
          <h2 id="auth-title">已有測試帳號？</h2>
          <div className={`status status--${connection.kind}`} role="status">
            <span className="status__dot" aria-hidden="true" />
            {connection.kind === 'loading' && '正在連接 API…'}
            {connection.kind === 'ready' &&
              `API 已連線 · ${connection.health.environment}`}
            {connection.kind === 'error' && 'API 尚未連線'}
          </div>
          <p className="auth__copy">
            作品導覽完全不需登入。這裡只供已配置帳號驗證完整
            CRUD、匯入與整合流程；所有資料請求仍由後端與 RLS 驗證權限。
          </p>
        </div>

        <div className="auth__controls">
          {auth.state.kind === 'unconfigured' && (
            <div className="demo-invite">
              <p className="auth__notice">
                尚未設定瀏覽器登入。請先填入 VITE_SUPABASE_URL 與
                VITE_SUPABASE_ANON_KEY，或開啟不連線的合成資料示範。
              </p>
              <button
                onClick={() => setShowDemo((value) => !value)}
                type="button"
              >
                {showDemo ? '關閉班表介面' : '查看班表唯讀介面'}
              </button>
            </div>
          )}

          {auth.state.kind === 'loading' && (
            <p className="auth__notice">正在確認登入狀態…</p>
          )}

          {auth.state.kind === 'signed-out' && (
            <div className="demo-invite">
              <form onSubmit={handleSignIn}>
                <label>
                  電子郵件
                  <input
                    autoComplete="email"
                    name="email"
                    onChange={(event) => setEmail(event.target.value)}
                    required
                    type="email"
                    value={email}
                  />
                </label>
                <label>
                  密碼
                  <input
                    autoComplete="current-password"
                    name="password"
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    type="password"
                    value={password}
                  />
                </label>
                <button disabled={auth.isSubmitting} type="submit">
                  {auth.isSubmitting ? '登入中…' : '登入'}
                </button>
              </form>
              <button
                onClick={() => setShowDemo((value) => !value)}
                type="button"
              >
                {showDemo ? '關閉班表介面' : '查看班表唯讀介面'}
              </button>
            </div>
          )}

          {auth.state.kind === 'signed-in' && (
            <div className="auth__signed-in">
              <div>
                <span>已登入</span>
                <strong>{auth.state.session.email}</strong>
              </div>
              <button
                disabled={auth.isSubmitting}
                onClick={() => void auth.signOut()}
                type="button"
              >
                {auth.isSubmitting ? '登出中…' : '登出'}
              </button>
            </div>
          )}

          {auth.actionError && (
            <p className="auth__error" role="alert">
              {auth.actionError}
            </p>
          )}
        </div>
      </section>

      {auth.state.kind === 'signed-in' && <Workspace client={apiClient} />}

      {(auth.state.kind === 'unconfigured' ||
        auth.state.kind === 'signed-out') &&
        showDemo && (
          <div className="demo-workspace">
            <p>唯讀合成資料 · 不連線、不建立帳號、不寫入資料庫</p>
            <Workspace
              client={syntheticDemoClient}
              initialDate="2026-09-02"
              readOnly
            />
          </div>
        )}
    </main>
  )
}
