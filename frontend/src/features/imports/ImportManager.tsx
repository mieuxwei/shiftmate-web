import { type FormEvent, useEffect, useState } from 'react'

import type { ApiError } from '../../api/client'
import type { ImportItem, ImportItemUpdate, ShiftImport } from '../../api/types'

export type ImportClient = {
  createImport: (file: File) => Promise<ShiftImport>
  updateImportItem: (
    importId: string,
    itemId: string,
    payload: ImportItemUpdate,
  ) => Promise<ShiftImport>
  commitImport: (importId: string) => Promise<{ created_shift_ids: string[] }>
}

type ImportManagerProps = {
  client: ImportClient
  timezone: string
  onCommitted: () => void
}

const ERROR_LABELS: Record<string, string> = {
  GEMINI_NOT_CONFIGURED: '尚未設定 Gemini，手動班表仍可使用。',
  GEMINI_QUOTA_EXHAUSTED: 'Gemini 免費配額已用完，請稍後重新上傳。',
  GEMINI_TIMEOUT: '辨識逾時，請重新上傳再試一次。',
  GEMINI_UNAVAILABLE: 'Gemini 暫時無法使用，請稍後重新上傳。',
  GEMINI_INVALID_RESPONSE: '辨識結果格式不完整，請重新上傳或改用手動新增。',
}

export function ImportManager({
  client,
  timezone,
  onCommitted,
}: ImportManagerProps) {
  const [current, setCurrent] = useState<ShiftImport | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [source, setSource] = useState<{
    name: string
    type: string
    url: string | null
  } | null>(null)

  useEffect(
    () => () => {
      if (source?.url) URL.revokeObjectURL(source.url)
    },
    [source],
  )

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const input = form.elements.namedItem('schedule') as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    const url =
      typeof URL.createObjectURL === 'function'
        ? URL.createObjectURL(file)
        : null
    setSource({ name: file.name, type: file.type, url })
    setBusy(true)
    setMessage(null)
    try {
      const result = await client.createImport(file)
      setCurrent(result)
      if (result.status === 'failed') {
        setMessage(
          ERROR_LABELS[result.error_code ?? ''] ?? '辨識失敗，請重新上傳。',
        )
      }
      form.reset()
    } catch (error) {
      const detail = (error as ApiError).detail
      setMessage(
        detail === 'UPLOAD_TOO_LARGE'
          ? '檔案不可超過 5 MB。'
          : '檔案格式不符；請使用有效的 JPG、PNG 或最多 40 頁 PDF。',
      )
    } finally {
      setBusy(false)
    }
  }

  async function saveItem(itemId: string, payload: ImportItemUpdate) {
    if (!current) return
    setBusy(true)
    setMessage(null)
    try {
      setCurrent(await client.updateImportItem(current.id, itemId, payload))
    } catch {
      setMessage('無法儲存這筆候選班次，請檢查日期與時間。')
    } finally {
      setBusy(false)
    }
  }

  async function commit() {
    if (!current) return
    setBusy(true)
    setMessage(null)
    try {
      const result = await client.commitImport(current.id)
      setCurrent({ ...current, status: 'committed' })
      setMessage(`已建立 ${result.created_shift_ids.length} 筆班次。`)
      onCommitted()
    } catch {
      setMessage('請先確認至少一筆有效候選班次。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="manager import-manager" aria-labelledby="import-title">
      <div className="section-heading">
        <div>
          <p className="section-kicker">Review before write</p>
          <h2 id="import-title">智慧匯入</h2>
        </div>
        <p>JPG、PNG 或 PDF · 5 MB · PDF 最多 40 頁</p>
      </div>

      <form
        aria-label="上傳班表"
        className="import-upload"
        onSubmit={(event) => void upload(event)}
      >
        <input
          accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
          aria-label="班表檔案"
          name="schedule"
          required
          type="file"
        />
        <button className="primary-action" disabled={busy} type="submit">
          {busy ? '處理中…' : '上傳並辨識'}
        </button>
      </form>
      <p className="calculation-note">
        僅上傳合成或匿名班表。辨識結果只會建立草稿，需逐筆確認後才寫入班表。
      </p>
      {source && (
        <div className="import-source">
          <strong>本機原始來源：{source.name}</strong>
          {source.url && source.type.startsWith('image/') && (
            <img alt={`待核對的原始班表 ${source.name}`} src={source.url} />
          )}
          {source.url && source.type === 'application/pdf' && (
            <object
              aria-label={`待核對的原始班表 ${source.name}`}
              data={source.url}
              type="application/pdf"
            />
          )}
        </div>
      )}

      {message && (
        <p className="import-message" role="status">
          {message}
        </p>
      )}
      {current?.status === 'review' && (
        <div className="import-review">
          <div className="import-review__summary">
            <strong>{current.items.length} 筆候選班次</strong>
            <span>
              {current.model_name} · {current.prompt_version}
            </span>
          </div>
          {current.items.length === 0 && (
            <p className="workspace-empty">
              沒有辨識到班次，請重新上傳或手動新增。
            </p>
          )}
          {current.items.map((item) => (
            <ImportItemEditor
              disabled={busy}
              item={item}
              key={item.id}
              onSave={(payload) => void saveItem(item.id, payload)}
              timezone={timezone}
            />
          ))}
          <button
            className="primary-action"
            disabled={busy || !current.items.some((item) => item.confirmed)}
            onClick={() => void commit()}
            type="button"
          >
            寫入已確認班次
          </button>
        </div>
      )}
    </section>
  )
}

function ImportItemEditor({
  item,
  timezone,
  disabled,
  onSave,
}: {
  item: ImportItem
  timezone: string
  disabled: boolean
  onSave: (payload: ImportItemUpdate) => void
}) {
  const [draft, setDraft] = useState(() => itemDraft(item, timezone))

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSave({
      work_date: draft.workDate || null,
      start_time: draft.startTime || null,
      end_time: draft.endTime || null,
      crosses_midnight: draft.crossesMidnight,
      break_minutes: Number(draft.breakMinutes),
      shift_type: draft.shiftType,
      notes: draft.notes || null,
      confirmed: draft.confirmed,
    })
  }

  return (
    <form className="import-item" onSubmit={submit}>
      <div className="form-grid">
        <label>
          日期
          <input
            onChange={(event) =>
              setDraft({ ...draft, workDate: event.target.value })
            }
            required
            type="date"
            value={draft.workDate}
          />
        </label>
        <label>
          班別
          <input
            onChange={(event) =>
              setDraft({ ...draft, shiftType: event.target.value })
            }
            required
            value={draft.shiftType}
          />
        </label>
        <label>
          開始
          <input
            onChange={(event) =>
              setDraft({ ...draft, startTime: event.target.value })
            }
            required
            type="time"
            value={draft.startTime}
          />
        </label>
        <label>
          結束
          <input
            onChange={(event) =>
              setDraft({ ...draft, endTime: event.target.value })
            }
            required
            type="time"
            value={draft.endTime}
          />
        </label>
        <label>
          休息分鐘
          <input
            min="0"
            max="1440"
            onChange={(event) =>
              setDraft({ ...draft, breakMinutes: event.target.value })
            }
            required
            type="number"
            value={draft.breakMinutes}
          />
        </label>
        <label className="check-label">
          <input
            checked={draft.crossesMidnight}
            onChange={(event) =>
              setDraft({ ...draft, crossesMidnight: event.target.checked })
            }
            type="checkbox"
          />
          跨日班次
        </label>
      </div>
      <label>
        備註
        <input
          onChange={(event) =>
            setDraft({ ...draft, notes: event.target.value })
          }
          value={draft.notes}
        />
      </label>
      {item.warnings.length > 0 && (
        <p className="import-warnings">{item.warnings.join(' · ')}</p>
      )}
      <div className="form-actions">
        <label className="check-label">
          <input
            checked={draft.confirmed}
            onChange={(event) =>
              setDraft({ ...draft, confirmed: event.target.checked })
            }
            type="checkbox"
          />
          我已核對原始班表
        </label>
        <button disabled={disabled} type="submit">
          儲存這筆
        </button>
      </div>
    </form>
  )
}

function itemDraft(item: ImportItem, timezone: string) {
  const start = zonedParts(item.start_at, timezone)
  const end = zonedParts(item.end_at, timezone)
  return {
    workDate: item.work_date ?? '',
    startTime: start,
    endTime: end,
    crossesMidnight: Boolean(
      item.start_at &&
      item.end_at &&
      localDate(item.end_at, timezone) > localDate(item.start_at, timezone),
    ),
    breakMinutes: String(item.break_minutes ?? 0),
    shiftType: item.shift_type ?? 'other',
    notes: item.notes ?? '',
    confirmed: item.confirmed,
  }
}

function zonedParts(value: string | null, timezone: string): string {
  if (!value) return ''
  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone: timezone,
  }).format(new Date(value))
}

function localDate(value: string, timezone: string): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone: timezone,
  }).formatToParts(new Date(value))
  const get = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? ''
  return `${get('year')}-${get('month')}-${get('day')}`
}
