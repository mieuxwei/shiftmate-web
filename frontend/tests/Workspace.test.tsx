import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AnalyticsSummary, Shift } from '../src/api/types'
import {
  Workspace,
  type WorkspaceClient,
} from '../src/features/workspace/Workspace'

const summary: AnalyticsSummary = {
  date_from: '2026-09-01',
  date_to: '2026-09-30',
  timezone: 'Asia/Taipei',
  currency: 'TWD',
  shift_count: 1,
  total_paid_hours: '7.5',
  estimated_pay: '1500.00',
  shift_type_counts: { day: 1 },
  weekly_hours: { '2026-08-31': '7.5' },
  longest_consecutive_days: 1,
}

const shifts: Shift[] = [
  {
    id: '00000000-0000-0000-0000-000000000001',
    work_date: '2026-09-02',
    start_at: '2026-09-02T01:00:00Z',
    end_at: '2026-09-02T09:00:00Z',
    break_minutes: 30,
    shift_type: 'day',
    notes: 'Synthetic shift',
    source: 'manual',
    created_at: '2026-09-01T00:00:00Z',
    updated_at: '2026-09-01T00:00:00Z',
  },
]

function clientWith(
  shiftResult: Shift[] = shifts,
  summaryResult: AnalyticsSummary = summary,
): WorkspaceClient {
  return {
    listShifts: vi.fn().mockResolvedValue(shiftResult),
    getAnalyticsSummary: vi.fn().mockResolvedValue(summaryResult),
    createShift: vi.fn(),
    updateShift: vi.fn(),
    deleteShift: vi.fn(),
    listPayRates: vi.fn().mockResolvedValue([]),
    createPayRate: vi.fn(),
    updatePayRate: vi.fn(),
    deletePayRate: vi.fn(),
  }
}

describe('Workspace', () => {
  afterEach(cleanup)

  it('renders deterministic summary and month schedule data', async () => {
    render(<Workspace client={clientWith()} initialDate="2026-09-02" />)

    expect(await screen.findByText(/1,500/)).toBeInTheDocument()
    expect(screen.getAllByText('7.5')).not.toHaveLength(0)
    expect(screen.getByText('09:00–17:00')).toBeInTheDocument()
    expect(
      screen.getByRole('img', { name: '每週工時趨勢圖' }),
    ).toBeInTheDocument()
  })

  it('switches to a Monday-to-Sunday week and refetches', async () => {
    const client = clientWith()
    render(<Workspace client={client} initialDate="2026-09-02" />)
    await screen.findByText(/1,500/)

    fireEvent.click(screen.getByRole('button', { name: '週' }))

    expect(
      await screen.findByRole('heading', { name: '週班表' }),
    ).toBeInTheDocument()
    expect(client.listShifts).toHaveBeenLastCalledWith(
      { dateFrom: '2026-08-31', dateTo: '2026-09-06' },
      expect.any(AbortSignal),
    )
  })

  it('renders a clear empty state', async () => {
    render(
      <Workspace
        client={clientWith([], {
          ...summary,
          shift_count: 0,
          total_paid_hours: '0',
          estimated_pay: '0.00',
          shift_type_counts: {},
          weekly_hours: {},
          longest_consecutive_days: 0,
        })}
        initialDate="2026-09-02"
      />,
    )

    expect(await screen.findByText('這個期間還沒有班次。')).toBeInTheDocument()
  })

  it('renders a safe error without backend details', async () => {
    const client = clientWith()
    vi.mocked(client.listShifts).mockRejectedValue(new Error('private detail'))
    render(<Workspace client={client} initialDate="2026-09-02" />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '無法載入這個期間',
    )
    expect(screen.queryByText('private detail')).not.toBeInTheDocument()
  })
})
