import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Shift } from '../src/api/types'
import {
  ShiftManager,
  type ShiftMutationClient,
} from '../src/features/schedule/ShiftManager'

const shift: Shift = {
  id: '00000000-0000-0000-0000-000000000001',
  work_date: '2026-09-02',
  start_at: '2026-09-02T01:00:00Z',
  end_at: '2026-09-02T09:00:00Z',
  break_minutes: 30,
  shift_type: 'day',
  notes: 'Synthetic shift',
  source: 'manual',
  created_at: '2026-09-01T00:00:00Z',
  updated_at: '2026-09-01T00:00:00Z',
}

function mutationClient() {
  const createShift = vi.fn().mockResolvedValue(shift)
  const updateShift = vi.fn().mockResolvedValue(shift)
  const deleteShift = vi.fn().mockResolvedValue(undefined)
  const client: ShiftMutationClient = {
    createShift,
    updateShift,
    deleteShift,
  }
  return { client, createShift, updateShift, deleteShift }
}

function renderManager(client: ShiftMutationClient, onChanged = vi.fn()) {
  render(
    <ShiftManager
      client={client}
      defaultDate="2026-09-02"
      onChanged={onChanged}
      shifts={[shift]}
      timezone="Asia/Taipei"
    />,
  )
  return onChanged
}

describe('ShiftManager', () => {
  afterEach(cleanup)

  it('creates a shift with timezone-aware UTC timestamps', async () => {
    const { client, createShift } = mutationClient()
    const onChanged = renderManager(client)

    fireEvent.click(screen.getByRole('button', { name: '新增班次' }))
    fireEvent.change(screen.getByLabelText('班別'), {
      target: { value: 'night' },
    })
    fireEvent.change(screen.getByLabelText('休息分鐘'), {
      target: { value: '45' },
    })
    fireEvent.click(screen.getByRole('button', { name: '儲存班次' }))

    await waitFor(() => {
      expect(createShift).toHaveBeenCalledWith({
        start_at: '2026-09-02T01:00:00.000Z',
        end_at: '2026-09-02T09:00:00.000Z',
        break_minutes: 45,
        shift_type: 'night',
        notes: null,
      })
    })
    expect(onChanged).toHaveBeenCalledOnce()
  })

  it('updates an existing shift', async () => {
    const { client, updateShift } = mutationClient()
    const onChanged = renderManager(client)

    fireEvent.click(screen.getByRole('button', { name: '編輯' }))
    fireEvent.change(screen.getByLabelText('備註'), {
      target: { value: 'Updated synthetic note' },
    })
    fireEvent.click(screen.getByRole('button', { name: '儲存班次' }))

    await waitFor(() => {
      expect(updateShift).toHaveBeenCalledWith(
        shift.id,
        expect.objectContaining({ notes: 'Updated synthetic note' }),
      )
    })
    expect(onChanged).toHaveBeenCalledOnce()
  })

  it('requires an explicit second action before deleting', async () => {
    const { client, deleteShift } = mutationClient()
    const onChanged = renderManager(client)

    fireEvent.click(screen.getByRole('button', { name: '刪除' }))
    expect(deleteShift).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: '確認刪除' }))

    await waitFor(() => expect(deleteShift).toHaveBeenCalledWith(shift.id))
    expect(onChanged).toHaveBeenCalledOnce()
  })
})
