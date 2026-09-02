import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App } from '../src/app/App'

describe('App', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
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

    render(<App />)

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      '你的班表，清楚而安心。',
    )
    expect(await screen.findByRole('status')).toHaveTextContent(
      'API 已連線 · development',
    )
  })

  it('shows a safe disconnected state when the API fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    render(<App />)

    expect(await screen.findByRole('status')).toHaveTextContent('API 尚未連線')
  })
})
