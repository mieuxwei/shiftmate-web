import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PayRate } from '../src/api/types'
import {
  PayRateManager,
  type PayRateClient,
} from '../src/features/payRates/PayRateManager'

const rate: PayRate = {
  id: '00000000-0000-0000-0000-000000000010',
  hourly_rate: '200.00',
  effective_from: '2026-01-01',
  effective_to: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function rateClient(rates: PayRate[] = [rate]) {
  const listPayRates = vi.fn().mockResolvedValue(rates)
  const createPayRate = vi.fn().mockResolvedValue(rate)
  const updatePayRate = vi.fn().mockResolvedValue(rate)
  const deletePayRate = vi.fn().mockResolvedValue(undefined)
  const client: PayRateClient = {
    listPayRates,
    createPayRate,
    updatePayRate,
    deletePayRate,
  }
  return {
    client,
    listPayRates,
    createPayRate,
    updatePayRate,
    deletePayRate,
  }
}

describe('PayRateManager', () => {
  afterEach(cleanup)

  it('loads rates and creates an open-ended rate', async () => {
    const { client, createPayRate } = rateClient([])
    render(<PayRateManager client={client} />)
    await screen.findByText('尚未設定時薪。')

    fireEvent.click(screen.getByRole('button', { name: '新增費率' }))
    fireEvent.change(screen.getByLabelText('每小時金額'), {
      target: { value: '220.50' },
    })
    fireEvent.change(screen.getByLabelText('生效日'), {
      target: { value: '2026-10-01' },
    })
    fireEvent.click(screen.getByRole('button', { name: '儲存費率' }))

    await waitFor(() =>
      expect(createPayRate).toHaveBeenCalledWith({
        hourly_rate: '220.50',
        effective_from: '2026-10-01',
        effective_to: null,
      }),
    )
  })

  it('updates an effective period', async () => {
    const { client, updatePayRate } = rateClient()
    render(<PayRateManager client={client} />)
    await screen.findByText('200.00')

    fireEvent.click(screen.getByRole('button', { name: '編輯費率' }))
    fireEvent.change(screen.getByLabelText('結束日（可留空）'), {
      target: { value: '2026-12-31' },
    })
    fireEvent.click(screen.getByRole('button', { name: '儲存費率' }))

    await waitFor(() =>
      expect(updatePayRate).toHaveBeenCalledWith(rate.id, {
        hourly_rate: '200.00',
        effective_from: '2026-01-01',
        effective_to: '2026-12-31',
      }),
    )
  })

  it('requires confirmation and reports protected deletion safely', async () => {
    const { client, deletePayRate } = rateClient()
    deletePayRate.mockRejectedValue(new Error('internal constraint detail'))
    render(<PayRateManager client={client} />)
    await screen.findByText('200.00')

    fireEvent.click(screen.getByRole('button', { name: '刪除費率' }))
    expect(deletePayRate).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: '確認刪除費率' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('未被班次使用')
    expect(
      screen.queryByText('internal constraint detail'),
    ).not.toBeInTheDocument()
  })
})
