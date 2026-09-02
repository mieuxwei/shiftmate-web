import type {
  AnalyticsSummary,
  DateRange,
  PayRate,
  PayRateCreate,
  PayRateUpdate,
  Shift,
  ShiftCreate,
  ShiftUpdate,
} from './types'

export type AccessTokenProvider = () => string | null

export class AuthenticationRequiredError extends Error {
  constructor() {
    super('An authenticated session is required')
    this.name = 'AuthenticationRequiredError'
  }
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail)
    this.name = 'ApiError'
  }
}

function dateRangeQuery(range: DateRange): string {
  return new URLSearchParams({
    date_from: range.dateFrom,
    date_to: range.dateTo,
  }).toString()
}

export class ApiClient {
  constructor(private readonly getAccessToken: AccessTokenProvider) {}

  listShifts(
    range?: Partial<DateRange>,
    signal?: AbortSignal,
  ): Promise<Shift[]> {
    const query = new URLSearchParams()
    if (range?.dateFrom) query.set('date_from', range.dateFrom)
    if (range?.dateTo) query.set('date_to', range.dateTo)
    const suffix = query.size > 0 ? `?${query.toString()}` : ''
    return this.request(`/api/v1/shifts${suffix}`, { signal })
  }

  createShift(payload: ShiftCreate): Promise<Shift> {
    return this.request('/api/v1/shifts', this.jsonRequest('POST', payload))
  }

  updateShift(shiftId: string, payload: ShiftUpdate): Promise<Shift> {
    return this.request(
      `/api/v1/shifts/${encodeURIComponent(shiftId)}`,
      this.jsonRequest('PATCH', payload),
    )
  }

  deleteShift(shiftId: string): Promise<void> {
    return this.request(`/api/v1/shifts/${encodeURIComponent(shiftId)}`, {
      method: 'DELETE',
    })
  }

  listPayRates(signal?: AbortSignal): Promise<PayRate[]> {
    return this.request('/api/v1/pay-rates', { signal })
  }

  createPayRate(payload: PayRateCreate): Promise<PayRate> {
    return this.request('/api/v1/pay-rates', this.jsonRequest('POST', payload))
  }

  updatePayRate(payRateId: string, payload: PayRateUpdate): Promise<PayRate> {
    return this.request(
      `/api/v1/pay-rates/${encodeURIComponent(payRateId)}`,
      this.jsonRequest('PATCH', payload),
    )
  }

  deletePayRate(payRateId: string): Promise<void> {
    return this.request(`/api/v1/pay-rates/${encodeURIComponent(payRateId)}`, {
      method: 'DELETE',
    })
  }

  getAnalyticsSummary(
    range: DateRange,
    signal?: AbortSignal,
  ): Promise<AnalyticsSummary> {
    return this.request(`/api/v1/analytics/summary?${dateRangeQuery(range)}`, {
      signal,
    })
  }

  private jsonRequest(method: 'POST' | 'PATCH', payload: object): RequestInit {
    return {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const accessToken = this.getAccessToken()
    if (!accessToken) throw new AuthenticationRequiredError()

    const headers = new Headers(init.headers)
    headers.set('Authorization', `Bearer ${accessToken}`)
    const response = await fetch(path, { ...init, headers })

    if (!response.ok) {
      let detail = `API request failed with status ${response.status}`
      try {
        const body = (await response.json()) as { detail?: unknown }
        if (typeof body.detail === 'string') detail = body.detail
      } catch {
        // Keep the safe status-based fallback for non-JSON error responses.
      }
      throw new ApiError(response.status, detail)
    }

    if (response.status === 204) return undefined as T
    return (await response.json()) as T
  }
}
