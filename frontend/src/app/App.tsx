import { type FormEvent, useEffect, useMemo, useState } from 'react'

import { ApiClient, type AccessTokenProvider } from '../api/client'
import { getHealth, type HealthStatus } from '../api/health'
import { configuredAuthGateway, type AuthGateway } from '../auth/session'
import { useAuthSession } from '../auth/useAuthSession'
import { syntheticDemoClient } from '../demo/syntheticDemo'
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
  const [connection, setConnection] = useState<ConnectionState>({
    kind: 'loading',
  })
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showDemo, setShowDemo] = useState(false)
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

  return (
    <main>
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">ShiftMate Web</p>
        <h1 id="page-title">你的班表，清楚而安心。</h1>
        <p className="lede">
          這是使用合成資料的開發展示環境。登入後可管理班表與費率，也可先開啟唯讀示範。
        </p>

        <div className={`status status--${connection.kind}`} role="status">
          <span className="status__dot" aria-hidden="true" />
          {connection.kind === 'loading' && '正在連接 API…'}
          {connection.kind === 'ready' &&
            `API 已連線 · ${connection.health.environment}`}
          {connection.kind === 'error' && 'API 尚未連線'}
        </div>
      </section>

      <section className="auth" aria-labelledby="auth-title" aria-live="polite">
        <div>
          <p className="auth__kicker">Secure session</p>
          <h2 id="auth-title">登入工作區</h2>
          <p className="auth__copy">
            瀏覽器只保留 Supabase 使用者
            session；所有班表與薪資請求仍由後端驗證權限。
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
                {showDemo ? '關閉合成示範' : '查看合成資料示範'}
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
                {showDemo ? '關閉合成示範' : '查看合成資料示範'}
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
