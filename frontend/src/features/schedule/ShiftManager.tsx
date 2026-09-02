import { type FormEvent, useState } from 'react'

import type { ApiClient } from '../../api/client'
import type { Shift, ShiftCreate } from '../../api/types'
import { isoToLocalInput, localInputToIso } from './dateTime'

export type ShiftMutationClient = Pick<
  ApiClient,
  'createShift' | 'updateShift' | 'deleteShift'
>

type ShiftManagerProps = {
  client: ShiftMutationClient
  shifts: Shift[]
  timezone: string
  defaultDate: string
  onChanged: () => void
}

type EditorState = { kind: 'create' } | { kind: 'edit'; shift: Shift }

function defaultStart(date: string): string {
  return `${date}T09:00`
}

function defaultEnd(date: string): string {
  return `${date}T17:00`
}

export function ShiftManager({
  client,
  shifts,
  timezone,
  defaultDate,
  onChanged,
}: ShiftManagerProps) {
  const [editor, setEditor] = useState<EditorState | null>(null)
  const [pendingDelete, setPendingDelete] = useState<string | null>(null)
  const [mutationError, setMutationError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function deleteShift(shiftId: string) {
    setBusy(true)
    setMutationError(null)
    try {
      await client.deleteShift(shiftId)
      setPendingDelete(null)
      onChanged()
    } catch {
      setMutationError('無法刪除班次，請稍後再試。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="manager" aria-labelledby="shift-manager-title">
      <div className="section-heading">
        <div>
          <p className="section-kicker">Manual CRUD</p>
          <h2 id="shift-manager-title">班次管理</h2>
        </div>
        <button
          className="primary-action"
          onClick={() => setEditor({ kind: 'create' })}
          type="button"
        >
          新增班次
        </button>
      </div>

      {editor && (
        <ShiftEditor
          client={client}
          defaultDate={defaultDate}
          editor={editor}
          onCancel={() => setEditor(null)}
          onSaved={() => {
            setEditor(null)
            onChanged()
          }}
          timezone={timezone}
        />
      )}

      <div className="management-list">
        {shifts.map((shift) => (
          <article key={shift.id}>
            <div>
              <strong>
                {shift.work_date} · {shift.shift_type}
              </strong>
              <span>
                {isoToLocalInput(shift.start_at, timezone).slice(11)}–
                {isoToLocalInput(shift.end_at, timezone).slice(11)} · 休息{' '}
                {shift.break_minutes} 分
              </span>
            </div>
            <div className="row-actions">
              <button
                onClick={() => setEditor({ kind: 'edit', shift })}
                type="button"
              >
                編輯
              </button>
              {pendingDelete === shift.id ? (
                <>
                  <button
                    className="danger-action"
                    disabled={busy}
                    onClick={() => void deleteShift(shift.id)}
                    type="button"
                  >
                    確認刪除
                  </button>
                  <button onClick={() => setPendingDelete(null)} type="button">
                    取消
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setPendingDelete(shift.id)}
                  type="button"
                >
                  刪除
                </button>
              )}
            </div>
          </article>
        ))}
        {shifts.length === 0 && <p>目前沒有可編輯的班次。</p>}
      </div>
      {mutationError && (
        <p className="form-error" role="alert">
          {mutationError}
        </p>
      )}
    </section>
  )
}

function ShiftEditor({
  client,
  editor,
  timezone,
  defaultDate,
  onSaved,
  onCancel,
}: {
  client: ShiftMutationClient
  editor: EditorState
  timezone: string
  defaultDate: string
  onSaved: () => void
  onCancel: () => void
}) {
  const existing = editor.kind === 'edit' ? editor.shift : null
  const [startAt, setStartAt] = useState(
    existing
      ? isoToLocalInput(existing.start_at, timezone)
      : defaultStart(defaultDate),
  )
  const [endAt, setEndAt] = useState(
    existing
      ? isoToLocalInput(existing.end_at, timezone)
      : defaultEnd(defaultDate),
  )
  const [breakMinutes, setBreakMinutes] = useState(
    String(existing?.break_minutes ?? 0),
  )
  const [shiftType, setShiftType] = useState(existing?.shift_type ?? 'day')
  const [notes, setNotes] = useState(existing?.notes ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const payload: ShiftCreate = {
        start_at: localInputToIso(startAt, timezone),
        end_at: localInputToIso(endAt, timezone),
        break_minutes: Number(breakMinutes),
        shift_type: shiftType.trim(),
        notes: notes.trim() || null,
      }
      if (existing) await client.updateShift(existing.id, payload)
      else await client.createShift(payload)
      onSaved()
    } catch {
      setError('無法儲存班次，請檢查時間、休息與班別。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="editor-form" onSubmit={(event) => void submit(event)}>
      <h3>{existing ? '編輯班次' : '新增班次'}</h3>
      <div className="form-grid">
        <label>
          開始
          <input
            name="start_at"
            onChange={(event) => setStartAt(event.target.value)}
            required
            type="datetime-local"
            value={startAt}
          />
        </label>
        <label>
          結束
          <input
            name="end_at"
            onChange={(event) => setEndAt(event.target.value)}
            required
            type="datetime-local"
            value={endAt}
          />
        </label>
        <label>
          休息分鐘
          <input
            max="1440"
            min="0"
            name="break_minutes"
            onChange={(event) => setBreakMinutes(event.target.value)}
            required
            type="number"
            value={breakMinutes}
          />
        </label>
        <label>
          班別
          <input
            maxLength={50}
            name="shift_type"
            onChange={(event) => setShiftType(event.target.value)}
            required
            value={shiftType}
          />
        </label>
      </div>
      <label>
        備註
        <textarea
          maxLength={1000}
          name="notes"
          onChange={(event) => setNotes(event.target.value)}
          value={notes}
        />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="form-actions">
        <button className="primary-action" disabled={busy} type="submit">
          {busy ? '儲存中…' : '儲存班次'}
        </button>
        <button disabled={busy} onClick={onCancel} type="button">
          取消
        </button>
      </div>
    </form>
  )
}
