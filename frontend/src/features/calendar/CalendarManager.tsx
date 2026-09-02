import { useEffect, useState } from 'react'

import type { ApiClient } from '../../api/client'
import type { CalendarStatus, DateRange } from '../../api/types'

export type CalendarClient = Pick<
  ApiClient,
  'getCalendarStatus' | 'connectCalendar' | 'syncCalendar' | 'exportCalendar'
>

const statusLabel: Record<CalendarStatus['connection_status'], string> = {
  disconnected: '尚未連線',
  active: '已連線',
  revoked: '授權已失效',
  error: '連線異常',
}

export function CalendarManager({
  client,
  range,
}: {
  client: CalendarClient
  range: DateRange
}) {
  const [status, setStatus] = useState<CalendarStatus | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    void client
      .getCalendarStatus(controller.signal)
      .then(setStatus)
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setMessage('無法讀取 Google Calendar 連線狀態。')
      })
    return () => controller.abort()
  }, [client])

  async function connect() {
    setBusy(true)
    setMessage(null)
    try {
      const result = await client.connectCalendar()
      window.location.assign(result.authorization_url)
    } catch {
      setMessage('Google Calendar OAuth 尚未設定或目前無法啟動。')
      setBusy(false)
    }
  }

  async function sync() {
    setBusy(true)
    setMessage(null)
    try {
      const result = await client.syncCalendar(range)
      setMessage(
        `同步完成：${result.synced} 個班次、${result.deleted} 個刪除；${result.failed} 個失敗。`,
      )
    } catch {
      setMessage('同步失敗；班表資料未被修改，可下載 ICS 或稍後重試。')
    } finally {
      setBusy(false)
    }
  }

  async function downloadIcs() {
    setBusy(true)
    setMessage(null)
    try {
      const blob = await client.exportCalendar(range)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'shiftmate-schedule.ics'
      anchor.click()
      URL.revokeObjectURL(url)
      setMessage('ICS 已下載；可匯入任何相容的日曆服務。')
    } catch {
      setMessage('目前無法建立 ICS，請稍後再試。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section
      className="manager calendar-manager"
      aria-labelledby="calendar-title"
    >
      <div className="section-heading">
        <div>
          <p className="section-kicker">Calendar export</p>
          <h2 id="calendar-title">日曆同步</h2>
        </div>
        <p>
          {status ? statusLabel[status.connection_status] : '正在讀取狀態…'}
        </p>
      </div>

      <p className="calendar-copy">
        Google
        授權只要求建立與管理活動的最小範圍。沒有授權時，仍可下載目前期間的 ICS。
      </p>
      <div className="calendar-actions">
        {status?.connection_status !== 'active' && (
          <button
            className="primary-action"
            disabled={busy || status?.configured === false}
            onClick={() => void connect()}
            type="button"
          >
            連結 Google Calendar
          </button>
        )}
        {status?.connection_status === 'active' && (
          <button
            className="primary-action"
            disabled={busy}
            onClick={() => void sync()}
            type="button"
          >
            同步目前期間
          </button>
        )}
        <button
          disabled={busy}
          onClick={() => void downloadIcs()}
          type="button"
        >
          下載 ICS
        </button>
      </div>
      {status?.configured === false && (
        <p className="calendar-hint">
          此環境未設定 Google OAuth；ICS 仍可使用。
        </p>
      )}
      {message && (
        <p className="policy-message" role="status">
          {message}
        </p>
      )}
    </section>
  )
}
