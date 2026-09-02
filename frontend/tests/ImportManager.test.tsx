import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ShiftImport } from '../src/api/types'
import {
  ImportManager,
  type ImportClient,
} from '../src/features/imports/ImportManager'

const draft: ShiftImport = {
  id: '00000000-0000-0000-0000-000000000401',
  filename: 'generated.png',
  media_type: 'image/png',
  status: 'review',
  model_name: 'synthetic-gemini',
  prompt_version: 'schedule_extraction_v1',
  error_code: null,
  created_at: '2026-09-02T00:00:00Z',
  updated_at: '2026-09-02T00:00:00Z',
  items: [
    {
      id: '00000000-0000-0000-0000-000000000402',
      work_date: '2026-09-03',
      start_at: '2026-09-03T14:00:00Z',
      end_at: '2026-09-03T22:00:00Z',
      break_minutes: 30,
      shift_type: 'night',
      notes: null,
      validation_status: 'valid',
      needs_review: true,
      warnings: ['MODEL_MARKED_FOR_REVIEW'],
      confirmed: false,
      committed_shift_id: null,
    },
  ],
}

function makeClient(): ImportClient {
  return {
    createImport: vi.fn().mockResolvedValue(draft),
    updateImportItem: vi.fn().mockResolvedValue({
      ...draft,
      items: [{ ...draft.items[0], confirmed: true }],
    }),
    commitImport: vi.fn().mockResolvedValue({ created_shift_ids: ['shift-1'] }),
  }
}

describe('ImportManager', () => {
  afterEach(cleanup)

  it('uploads, reviews, explicitly confirms, and commits a draft', async () => {
    const client = makeClient()
    const committed = vi.fn()
    render(
      <ImportManager
        client={client}
        onCommitted={committed}
        timezone="Asia/Taipei"
      />,
    )

    const input = screen.getByLabelText('班表檔案')
    fireEvent.change(input, {
      target: {
        files: [
          new File(['synthetic'], 'synthetic.png', { type: 'image/png' }),
        ],
      },
    })
    fireEvent.submit(screen.getByRole('form', { name: '上傳班表' }))

    expect(await screen.findByText('1 筆候選班次')).toBeInTheDocument()
    expect(screen.getByDisplayValue('22:00')).toBeInTheDocument()
    expect(screen.getByDisplayValue('06:00')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: '寫入已確認班次' }),
    ).toBeDisabled()

    fireEvent.click(screen.getByLabelText('我已核對原始班表'))
    fireEvent.click(screen.getByRole('button', { name: '儲存這筆' }))
    await waitFor(() => expect(client.updateImportItem).toHaveBeenCalledOnce())
    fireEvent.click(screen.getByRole('button', { name: '寫入已確認班次' }))

    expect(await screen.findByText('已建立 1 筆班次。')).toBeInTheDocument()
    expect(client.commitImport).toHaveBeenCalledOnce()
    expect(committed).toHaveBeenCalledOnce()
  })

  it('shows a retry-safe quota failure without raw provider content', async () => {
    const client = makeClient()
    vi.mocked(client.createImport).mockResolvedValue({
      ...draft,
      status: 'failed',
      error_code: 'GEMINI_QUOTA_EXHAUSTED',
      items: [],
    })
    render(
      <ImportManager client={client} onCommitted={vi.fn()} timezone="UTC" />,
    )

    fireEvent.change(screen.getByLabelText('班表檔案'), {
      target: {
        files: [
          new File(['synthetic'], 'synthetic.png', { type: 'image/png' }),
        ],
      },
    })
    fireEvent.submit(screen.getByRole('form', { name: '上傳班表' }))

    expect(
      await screen.findByText('Gemini 免費配額已用完，請稍後重新上傳。'),
    ).toBeInTheDocument()
  })
})
