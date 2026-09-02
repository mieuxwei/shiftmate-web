import { type FormEvent, useEffect, useState } from 'react'

import type { ApiClient } from '../../api/client'
import type { PayRate, PayRateCreate } from '../../api/types'

export type PayRateClient = Pick<
  ApiClient,
  'listPayRates' | 'createPayRate' | 'updatePayRate' | 'deletePayRate'
>

type EditorState = { kind: 'create' } | { kind: 'edit'; rate: PayRate }

export function PayRateManager({ client }: { client: PayRateClient }) {
  const [reloadVersion, setReloadVersion] = useState(0)
  return (
    <PayRateData
      client={client}
      key={reloadVersion}
      onChanged={() => setReloadVersion((value) => value + 1)}
    />
  )
}

function PayRateData({
  client,
  onChanged,
}: {
  client: PayRateClient
  onChanged: () => void
}) {
  const [rates, setRates] = useState<PayRate[] | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [editor, setEditor] = useState<EditorState | null>(null)
  const [pendingDelete, setPendingDelete] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [mutationError, setMutationError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    void client
      .listPayRates(controller.signal)
      .then(setRates)
      .catch((caught: unknown) => {
        if (caught instanceof DOMException && caught.name === 'AbortError')
          return
        setLoadError(true)
      })
    return () => controller.abort()
  }, [client])

  async function deleteRate(rateId: string) {
    setBusy(true)
    setMutationError(null)
    try {
      await client.deletePayRate(rateId)
      onChanged()
    } catch {
      setMutationError('無法刪除費率；請確認它未被班次使用。')
      setPendingDelete(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="manager" aria-labelledby="pay-rate-title">
      <div className="section-heading">
        <div>
          <p className="section-kicker">Effective rates</p>
          <h2 id="pay-rate-title">時薪管理</h2>
        </div>
        <button
          className="primary-action"
          onClick={() => setEditor({ kind: 'create' })}
          type="button"
        >
          新增費率
        </button>
      </div>

      {editor && (
        <PayRateEditor
          client={client}
          editor={editor}
          onCancel={() => setEditor(null)}
          onSaved={() => {
            setEditor(null)
            onChanged()
          }}
        />
      )}

      {loadError && (
        <p className="form-error" role="alert">
          無法載入時薪設定。
        </p>
      )}
      {!loadError && !rates && <p className="manager-loading">正在載入時薪…</p>}
      {rates && (
        <div className="management-list">
          {rates.map((rate) => (
            <article key={rate.id}>
              <div>
                <strong>{rate.hourly_rate}</strong>
                <span>
                  {rate.effective_from} – {rate.effective_to ?? '持續有效'}
                </span>
              </div>
              <div className="row-actions">
                <button
                  onClick={() => setEditor({ kind: 'edit', rate })}
                  type="button"
                >
                  編輯費率
                </button>
                {pendingDelete === rate.id ? (
                  <>
                    <button
                      className="danger-action"
                      disabled={busy}
                      onClick={() => void deleteRate(rate.id)}
                      type="button"
                    >
                      確認刪除費率
                    </button>
                    <button
                      onClick={() => setPendingDelete(null)}
                      type="button"
                    >
                      取消
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setPendingDelete(rate.id)}
                    type="button"
                  >
                    刪除費率
                  </button>
                )}
              </div>
            </article>
          ))}
          {rates.length === 0 && <p>尚未設定時薪。</p>}
        </div>
      )}
      {mutationError && (
        <p className="form-error" role="alert">
          {mutationError}
        </p>
      )}
    </section>
  )
}

function PayRateEditor({
  client,
  editor,
  onSaved,
  onCancel,
}: {
  client: PayRateClient
  editor: EditorState
  onSaved: () => void
  onCancel: () => void
}) {
  const existing = editor.kind === 'edit' ? editor.rate : null
  const [hourlyRate, setHourlyRate] = useState(existing?.hourly_rate ?? '')
  const [effectiveFrom, setEffectiveFrom] = useState(
    existing?.effective_from ?? '',
  )
  const [effectiveTo, setEffectiveTo] = useState(existing?.effective_to ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    const payload: PayRateCreate = {
      hourly_rate: hourlyRate,
      effective_from: effectiveFrom,
      effective_to: effectiveTo || null,
    }
    try {
      if (existing) await client.updatePayRate(existing.id, payload)
      else await client.createPayRate(payload)
      onSaved()
    } catch {
      setError('無法儲存費率；請檢查金額與有效期是否重疊。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="editor-form" onSubmit={(event) => void submit(event)}>
      <h3>{existing ? '編輯費率' : '新增費率'}</h3>
      <div className="form-grid form-grid--rates">
        <label>
          每小時金額
          <input
            min="0.01"
            name="hourly_rate"
            onChange={(event) => setHourlyRate(event.target.value)}
            required
            step="0.01"
            type="number"
            value={hourlyRate}
          />
        </label>
        <label>
          生效日
          <input
            name="effective_from"
            onChange={(event) => setEffectiveFrom(event.target.value)}
            required
            type="date"
            value={effectiveFrom}
          />
        </label>
        <label>
          結束日（可留空）
          <input
            min={effectiveFrom || undefined}
            name="effective_to"
            onChange={(event) => setEffectiveTo(event.target.value)}
            type="date"
            value={effectiveTo}
          />
        </label>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="form-actions">
        <button className="primary-action" disabled={busy} type="submit">
          {busy ? '儲存中…' : '儲存費率'}
        </button>
        <button disabled={busy} onClick={onCancel} type="button">
          取消
        </button>
      </div>
    </form>
  )
}
