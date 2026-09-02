import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ApiClient,
  ApiError,
  AuthenticationRequiredError,
} from '../src/api/client'

describe('ApiClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('adds the current bearer token and serializes date filters', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    const client = new ApiClient(() => 'synthetic-token')

    await client.listShifts({
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    })

    expect(fetchMock).toHaveBeenCalledOnce()
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(path).toBe('/api/v1/shifts?date_from=2026-09-01&date_to=2026-09-30')
    expect(new Headers(init.headers).get('Authorization')).toBe(
      'Bearer synthetic-token',
    )
  })

  it('uses typed analytics query parameters', async () => {
    const summary = {
      date_from: '2026-09-01',
      date_to: '2026-09-30',
      timezone: 'Asia/Taipei',
      currency: 'TWD',
      shift_count: 0,
      total_paid_hours: '0.00',
      estimated_pay: '0.00',
      shift_type_counts: {},
      weekly_hours: {},
      longest_consecutive_days: 0,
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(summary), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    const client = new ApiClient(() => 'synthetic-token')

    const result = await client.getAnalyticsSummary({
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    })

    expect(result).toEqual(summary)
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      '/api/v1/analytics/summary?date_from=2026-09-01&date_to=2026-09-30',
    )
  })

  it('does not call the API without an access token', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const client = new ApiClient(() => null)

    await expect(client.listPayRates()).rejects.toBeInstanceOf(
      AuthenticationRequiredError,
    )
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('preserves a safe API error detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Invalid date range' }), {
          status: 422,
        }),
      ),
    )
    const client = new ApiClient(() => 'synthetic-token')

    await expect(
      client.getAnalyticsSummary({
        dateFrom: '2026-09-30',
        dateTo: '2026-09-01',
      }),
    ).rejects.toEqual(new ApiError(422, 'Invalid date range'))
  })
})
