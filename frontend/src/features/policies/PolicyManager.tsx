import { type FormEvent, useEffect, useRef, useState } from 'react'

import type { ApiClient } from '../../api/client'
import type {
  PolicyAnswer,
  PolicyDocument,
  PolicyStatus,
} from '../../api/types'

export type PolicyClient = Pick<
  ApiClient,
  'listPolicies' | 'createPolicy' | 'deletePolicy' | 'queryPolicy'
>

const statusLabels: Record<PolicyStatus, string> = {
  uploaded: '已上傳',
  indexing: '建立索引中',
  ready: '可查詢',
  failed: '索引失敗',
}

export function PolicyManager({ client }: { client: PolicyClient }) {
  const [documents, setDocuments] = useState<PolicyDocument[] | null>(null)
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [confirmedSafeData, setConfirmedSafeData] = useState(false)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<PolicyAnswer | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const controller = new AbortController()
    void client
      .listPolicies(controller.signal)
      .then(setDocuments)
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setMessage('無法載入規章文件。')
      })
    return () => controller.abort()
  }, [client])

  async function uploadPolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file) return
    setBusy(true)
    setMessage(null)
    try {
      const result = await client.createPolicy(
        title.trim(),
        file,
        confirmedSafeData,
      )
      setDocuments((current) => {
        const others = (current ?? []).filter(
          (document) => document.id !== result.document.id,
        )
        return [result.document, ...others]
      })
      setMessage(
        result.duplicate
          ? '相同內容已存在，未重複建立索引。'
          : result.document.status === 'ready'
            ? '規章已建立索引，可以開始提問。'
            : '文件已保存，但目前無法完成索引。',
      )
      setTitle('')
      setFile(null)
      setConfirmedSafeData(false)
      if (fileInput.current) fileInput.current.value = ''
    } catch {
      setMessage('無法上傳規章；請確認檔案是 5 MB、40 頁內的有效 PDF。')
    } finally {
      setBusy(false)
    }
  }

  async function removePolicy(documentId: string) {
    setBusy(true)
    setMessage(null)
    try {
      await client.deletePolicy(documentId)
      setDocuments((current) =>
        (current ?? []).filter((document) => document.id !== documentId),
      )
      setAnswer(null)
    } catch {
      setMessage('無法刪除這份規章。')
    } finally {
      setBusy(false)
    }
  }

  async function askPolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setMessage(null)
    setAnswer(null)
    try {
      setAnswer(await client.queryPolicy(question.trim()))
    } catch {
      setMessage('目前無法查詢規章，既有班表功能仍可使用。')
    } finally {
      setBusy(false)
    }
  }

  const readyCount = (documents ?? []).filter(
    (document) => document.status === 'ready',
  ).length

  return (
    <section className="manager policy-manager" aria-labelledby="policy-title">
      <div className="section-heading">
        <div>
          <p className="section-kicker">Grounded policy RAG</p>
          <h2 id="policy-title">規章助理</h2>
        </div>
        <p>{readyCount} 份文件可查詢</p>
      </div>

      <form
        className="policy-upload"
        onSubmit={(event) => {
          void uploadPolicy(event)
        }}
      >
        <label>
          文件名稱
          <input
            maxLength={200}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="例如：2026 合成員工手冊"
            required
            value={title}
          />
        </label>
        <label>
          PDF 文件
          <input
            accept="application/pdf,.pdf"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            ref={fileInput}
            required
            type="file"
          />
        </label>
        <label className="policy-safe-data">
          <input
            checked={confirmedSafeData}
            onChange={(event) => setConfirmedSafeData(event.target.checked)}
            required
            type="checkbox"
          />
          我確認此 PDF 僅含合成或匿名化資料，不含私人班表、薪資或內部文件。
        </label>
        <button className="primary-action" disabled={busy} type="submit">
          {busy ? '處理中…' : '上傳並建立索引'}
        </button>
      </form>

      <div className="policy-documents" aria-label="已上傳規章">
        {documents === null && <p>正在載入規章…</p>}
        {documents?.length === 0 && <p>尚未上傳規章 PDF。</p>}
        {documents?.map((document) => (
          <article key={document.id}>
            <div>
              <strong>{document.title}</strong>
              <span>
                {statusLabels[document.status]}
                {document.page_count ? ` · ${document.page_count} 頁` : ''}
              </span>
            </div>
            <button
              className="danger-action"
              disabled={busy}
              onClick={() => void removePolicy(document.id)}
              type="button"
            >
              刪除
            </button>
          </article>
        ))}
      </div>

      <form
        className="policy-question"
        onSubmit={(event) => {
          void askPolicy(event)
        }}
      >
        <label>
          根據已上傳規章提問
          <textarea
            maxLength={1000}
            minLength={2}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="例如：每班休息時間如何規定？"
            required
            value={question}
          />
        </label>
        <button
          className="primary-action"
          disabled={busy || readyCount === 0}
          type="submit"
        >
          查詢規章
        </button>
      </form>

      {message && (
        <p className="policy-message" role="status">
          {message}
        </p>
      )}

      {answer && (
        <article className="policy-answer" aria-live="polite">
          <h3>{answer.refused ? '資料不足' : '依規章回答'}</h3>
          <p>{answer.answer}</p>
          {answer.citations.length > 0 && (
            <ol aria-label="引用來源">
              {answer.citations.map((citation) => (
                <li key={citation.chunk_id}>
                  <strong>
                    {citation.title}，第 {citation.page_number} 頁
                  </strong>
                  <blockquote>{citation.excerpt}</blockquote>
                </li>
              ))}
            </ol>
          )}
        </article>
      )}
    </section>
  )
}
