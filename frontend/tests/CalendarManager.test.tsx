import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { CalendarClient } from '../src/features/calendar/CalendarManager'
import { CalendarManager } from '../src/features/calendar/CalendarManager'

const range = { dateFrom: '2026-09-01', dateTo: '2026-09-30' }

function clientWithStatus(
  connection_status: 'disconnected' | 'active' | 'revoked' = 'disconnected',
  configured = true,
): CalendarClient {
  return {
    getCalendarStatus: vi.fn().mockResolvedValue({
      configured,
      connection_status,
      scopes: [],
      ics_available: true,
    }),
    connectCalendar: vi.fn().mockResolvedValue({
      authorization_url: 'https://accounts.google.com/o/oauth2/v2/auth',
    }),
    syncCalendar: vi
      .fn()
      .mockResolvedValue({ synced: 2, deleted: 1, failed: 0 }),
    exportCalendar: vi
      .fn()
      .mockResolvedValue(new Blob(['BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n'])),
  }
}

describe('CalendarManager', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('keeps ICS available when Google OAuth is unconfigured', async () => {
    const client = clientWithStatus('disconnected', false)
    const createObjectURL = vi.fn().mockReturnValue('blob:synthetic-calendar')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    render(<CalendarManager client={client} range={range} />)

    expect(await screen.findByText('尚未連線')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: '連結 Google Calendar' }),
    ).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: '下載 ICS' }))

    expect(await screen.findByText(/ICS 已下載/)).toBeInTheDocument()
    expect(client.exportCalendar).toHaveBeenCalledWith(range)
    expect(createObjectURL).toHaveBeenCalledOnce()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:synthetic-calendar')
  })

  it('syncs the visible date range for an active connection', async () => {
    const client = clientWithStatus('active')
    render(<CalendarManager client={client} range={range} />)

    fireEvent.click(await screen.findByRole('button', { name: '同步目前期間' }))

    expect(await screen.findByText(/2 個班次、1 個刪除/)).toBeInTheDocument()
    expect(client.syncCalendar).toHaveBeenCalledWith(range)
  })
})
