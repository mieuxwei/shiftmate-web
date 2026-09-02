import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PolicyDocument } from '../src/api/types'
import {
  PolicyManager,
  type PolicyClient,
} from '../src/features/policies/PolicyManager'

const document: PolicyDocument = {
  id: '00000000-0000-0000-0000-000000000101',
  title: '合成員工手冊',
  filename: 'generated.pdf',
  status: 'ready',
  page_count: 3,
  error_code: null,
  created_at: '2026-09-02T00:00:00Z',
  updated_at: '2026-09-02T00:00:00Z',
}

function policyClient(): PolicyClient {
  return {
    listPolicies: vi.fn().mockResolvedValue([document]),
    createPolicy: vi.fn().mockResolvedValue({
      document,
      duplicate: true,
    }),
    deletePolicy: vi.fn().mockResolvedValue(undefined),
  }
}

describe('PolicyManager', () => {
  afterEach(cleanup)

  it('uploads PDFs and reports SHA duplicate handling', async () => {
    const client = policyClient()
    render(<PolicyManager client={client} />)
    await screen.findByText('合成員工手冊')

    fireEvent.change(screen.getByLabelText('文件名稱'), {
      target: { value: '合成員工手冊' },
    })
    const file = new File(['%PDF-fixture'], 'policy.pdf', {
      type: 'application/pdf',
    })
    fireEvent.change(screen.getByLabelText('PDF 文件'), {
      target: { files: [file] },
    })
    fireEvent.click(screen.getByLabelText(/我確認此 PDF 僅含合成或匿名化資料/))
    const uploadButton = screen.getByRole('button', {
      name: '上傳並建立索引',
    })
    const uploadForm = uploadButton.closest('form')
    expect(uploadForm).not.toBeNull()
    fireEvent.submit(uploadForm!)

    expect(
      await screen.findByText('相同內容已存在，未重複建立索引。'),
    ).toBeInTheDocument()
    expect(client.createPolicy).toHaveBeenCalledWith('合成員工手冊', file, true)
  })

  it('deletes documents', async () => {
    const client = policyClient()
    render(<PolicyManager client={client} />)
    await screen.findByText('合成員工手冊')

    fireEvent.click(screen.getByRole('button', { name: '刪除' }))
    await waitFor(() =>
      expect(client.deletePolicy).toHaveBeenCalledWith(document.id),
    )
    expect(screen.queryByText('合成員工手冊')).not.toBeInTheDocument()
  })
})
