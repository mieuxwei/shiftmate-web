import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App } from '../src/app/App'
import type { AuthGateway, AuthSession } from '../src/auth/session'
import type { WorkspaceClient } from '../src/features/workspace/Workspace'

function signedOutGateway() {
  const signIn = vi.fn().mockResolvedValue({
    accessToken: 'synthetic-token',
    email: 'demo@example.com',
  })
  const signOut = vi.fn().mockResolvedValue(undefined)
  const getSession = vi
    .fn<() => Promise<AuthSession | null>>()
    .mockResolvedValue(null)
  const gateway: AuthGateway = {
    getSession,
    subscribe: vi.fn().mockReturnValue(() => undefined),
    signIn,
    signOut,
  }
  return { gateway, getSession, signIn, signOut }
}

function emptyWorkspaceClient(): WorkspaceClient {
  return {
    listShifts: vi.fn().mockResolvedValue([]),
    getAnalyticsSummary: vi.fn().mockResolvedValue({
      date_from: '2026-09-01',
      date_to: '2026-09-30',
      timezone: 'Asia/Taipei',
      currency: 'TWD',
      shift_count: 0,
      total_paid_hours: '0',
      estimated_pay: '0.00',
      shift_type_counts: {},
      weekly_hours: {},
      longest_consecutive_days: 0,
    }),
    createShift: vi.fn(),
    updateShift: vi.fn(),
    deleteShift: vi.fn(),
    listPayRates: vi.fn().mockResolvedValue([]),
    createPayRate: vi.fn(),
    updatePayRate: vi.fn(),
    deletePayRate: vi.fn(),
  }
}

describe('App', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    window.history.replaceState(null, '', '/')
  })

  it('shows the connected API environment', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ status: 'ok', environment: 'development' }),
            { status: 200 },
          ),
        ),
    )

    render(<App authGateway={null} />)

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      '從班表影像',
    )
    expect(await screen.findByRole('status')).toHaveTextContent(
      'API 已連線 · development',
    )
  })

  it('shows a safe disconnected state when the API fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    render(<App authGateway={null} />)

    expect(await screen.findByRole('status')).toHaveTextContent('API 尚未連線')
  })

  it('opens the credential-free synthetic read-only demo', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ status: 'ok', environment: 'development' }),
            { status: 200 },
          ),
        ),
    )
    render(<App authGateway={null} />)

    fireEvent.click(screen.getByRole('button', { name: '查看班表唯讀介面' }))

    expect(await screen.findByText(/8,000/)).toBeInTheDocument()
    expect(screen.getByText('22:00–06:00')).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: '新增班次' }),
    ).not.toBeInTheDocument()
  })

  it('signs in through the injected session gateway', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ status: 'ok', environment: 'development' }),
            { status: 200 },
          ),
        ),
    )
    const { gateway, signIn } = signedOutGateway()

    render(
      <App
        apiClientFactory={() => emptyWorkspaceClient()}
        authGateway={gateway}
      />,
    )

    fireEvent.change(await screen.findByLabelText('電子郵件'), {
      target: { value: 'demo@example.com' },
    })
    fireEvent.change(screen.getByLabelText('密碼'), {
      target: { value: 'synthetic-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: '登入' }))

    expect(await screen.findByText('demo@example.com')).toBeInTheDocument()
    expect(signIn).toHaveBeenCalledWith(
      'demo@example.com',
      'synthetic-password',
    )
  })

  it('keeps the synthetic demo available when production auth is configured', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ status: 'ok', environment: 'production' }),
            { status: 200 },
          ),
        ),
    )
    const { gateway } = signedOutGateway()

    render(<App authGateway={gateway} />)

    fireEvent.click(
      await screen.findByRole('button', { name: '查看班表唯讀介面' }),
    )

    expect(await screen.findByText(/8,000/)).toBeInTheDocument()
    expect(screen.getByText('22:00–06:00')).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: '新增班次' }),
    ).not.toBeInTheDocument()
  })

  it('opens the public interactive demo without signing in', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ status: 'ok', environment: 'production' }),
        {
          status: 200,
        },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { gateway, signIn } = signedOutGateway()

    render(<App authGateway={gateway} />)

    fireEvent.click(
      await screen.findByRole('button', { name: '免登入體驗互動 Demo' }),
    )

    expect(window.location.hash).toBe('#demo')
    expect(screen.getByText('Interactive Demo')).toBeInTheDocument()
    expect(
      screen.getByText('2 分鐘自助體驗 · 唯讀合成資料'),
    ).toBeInTheDocument()
    expect(signIn).not.toHaveBeenCalled()
    expect(fetchMock).toHaveBeenCalledOnce()

    fireEvent.click(screen.getByRole('button', { name: '返回首頁' }))
    expect(window.location.hash).toBe('')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      '從班表影像',
    )
  })

  it('supports a direct demo hash deep-link', () => {
    window.history.replaceState(null, '', '/#demo')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    render(<App authGateway={null} />)

    expect(screen.getByText('Interactive Demo')).toBeInTheDocument()
    expect(screen.queryByLabelText('電子郵件')).not.toBeInTheDocument()
  })

  it('shows an existing session and signs out safely', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ status: 'ok', environment: 'development' }),
            { status: 200 },
          ),
        ),
    )
    const existingSession: AuthSession = {
      accessToken: 'synthetic-token',
      email: 'owner@example.com',
    }
    const { gateway, getSession, signOut } = signedOutGateway()
    getSession.mockResolvedValue(existingSession)

    render(
      <App
        apiClientFactory={() => emptyWorkspaceClient()}
        authGateway={gateway}
      />,
    )

    expect(await screen.findByText('owner@example.com')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '登出' }))

    expect(await screen.findByLabelText('電子郵件')).toBeInTheDocument()
    expect(signOut).toHaveBeenCalledOnce()
  })
})
