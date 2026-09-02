import { useEffect, useMemo, useState } from 'react'

import type { ApiClient } from '../../api/client'
import type { AnalyticsSummary, DateRange, Shift } from '../../api/types'
import { Dashboard } from '../dashboard/Dashboard'
import { ImportManager, type ImportClient } from '../imports/ImportManager'
import { PayRateManager } from '../payRates/PayRateManager'
import {
  moveAnchor,
  periodLabel,
  rangeFor,
  type ScheduleViewMode,
  todayValue,
} from '../schedule/dateRange'
import { ScheduleView } from '../schedule/ScheduleView'
import { ShiftManager } from '../schedule/ShiftManager'

export type WorkspaceClient = Pick<
  ApiClient,
  | 'listShifts'
  | 'getAnalyticsSummary'
  | 'createShift'
  | 'updateShift'
  | 'deleteShift'
  | 'listPayRates'
  | 'createPayRate'
  | 'updatePayRate'
  | 'deletePayRate'
> &
  Partial<
    Pick<
      ApiClient,
      'createImport' | 'getImport' | 'updateImportItem' | 'commitImport'
    >
  >

type WorkspaceProps = {
  client: WorkspaceClient
  initialDate?: string
  readOnly?: boolean
}

type WorkspaceData = {
  shifts: Shift[]
  summary: AnalyticsSummary
}

export function Workspace({
  client,
  initialDate = todayValue(),
  readOnly = false,
}: WorkspaceProps) {
  const [mode, setMode] = useState<ScheduleViewMode>('month')
  const [anchor, setAnchor] = useState(initialDate)
  const [reloadVersion, setReloadVersion] = useState(0)
  const range = useMemo(() => rangeFor(mode, anchor), [mode, anchor])

  return (
    <section className="workspace" aria-label="班表工作區">
      <nav className="workspace-toolbar" aria-label="班表期間控制">
        <div className="view-switch" aria-label="檢視方式">
          <button
            aria-pressed={mode === 'month'}
            onClick={() => setMode('month')}
            type="button"
          >
            月
          </button>
          <button
            aria-pressed={mode === 'week'}
            onClick={() => setMode('week')}
            type="button"
          >
            週
          </button>
        </div>
        <div className="period-controls">
          <button
            aria-label="上一期"
            onClick={() => setAnchor(moveAnchor(mode, anchor, -1))}
            type="button"
          >
            ←
          </button>
          <strong>{periodLabel(mode, range)}</strong>
          <button
            aria-label="下一期"
            onClick={() => setAnchor(moveAnchor(mode, anchor, 1))}
            type="button"
          >
            →
          </button>
          <button onClick={() => setAnchor(todayValue())} type="button">
            今天
          </button>
        </div>
      </nav>

      {!readOnly && <PayRateManager client={client} />}

      <RangeData
        client={client}
        key={`${range.dateFrom}:${range.dateTo}:${reloadVersion}`}
        onChanged={() => setReloadVersion((version) => version + 1)}
        readOnly={readOnly}
        range={range}
        mode={mode}
      />
    </section>
  )
}

function RangeData({
  client,
  range,
  mode,
  onChanged,
  readOnly,
}: {
  client: WorkspaceClient
  range: DateRange
  mode: ScheduleViewMode
  onChanged: () => void
  readOnly: boolean
}) {
  const [data, setData] = useState<WorkspaceData | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    void Promise.all([
      client.listShifts(range, controller.signal),
      client.getAnalyticsSummary(range, controller.signal),
    ])
      .then(([shifts, summary]) => setData({ shifts, summary }))
      .catch((caught: unknown) => {
        if (caught instanceof DOMException && caught.name === 'AbortError')
          return
        setError(true)
      })
    return () => controller.abort()
  }, [client, range])

  if (error) {
    return (
      <div className="workspace-state" role="alert">
        <strong>無法載入這個期間</strong>
        <span>請確認 API 連線、登入狀態與費率設定。</span>
      </div>
    )
  }
  if (!data) return <div className="workspace-state">正在載入班表與摘要…</div>

  return (
    <>
      <Dashboard summary={data.summary} />
      {!readOnly && hasImportClient(client) && (
        <ImportManager
          client={client}
          onCommitted={onChanged}
          timezone={data.summary.timezone}
        />
      )}
      <ScheduleView
        mode={mode}
        range={range}
        shifts={data.shifts}
        timezone={data.summary.timezone}
      />
      {!readOnly && (
        <ShiftManager
          client={client}
          defaultDate={range.dateFrom}
          onChanged={onChanged}
          shifts={data.shifts}
          timezone={data.summary.timezone}
        />
      )}
    </>
  )
}

function hasImportClient(
  client: WorkspaceClient,
): client is WorkspaceClient & ImportClient {
  return Boolean(
    client.createImport && client.updateImportItem && client.commitImport,
  )
}
