import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import fixture from '../src/demo/schedule-demo.json'
import {
  demoShifts,
  demoTotals,
  scheduleImage,
} from '../src/demo/reviewerShowcase'
import { ReviewerShowcase } from '../src/features/reviewer/ReviewerShowcase'

const go = (name: RegExp) =>
  fireEvent.click(screen.getByRole('button', { name }))
describe('ReviewerShowcase', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })
  it('derives six rows, breaks, overnight pay and summary from the same fixture', () => {
    expect(demoTotals).toEqual({
      hours: 40,
      amount: 8000,
      count: 6,
      longest: 2,
    })
    expect(demoShifts[1]).toMatchObject({
      time: '22:00–06:00',
      grossHours: 8,
      breakMinutes: 30,
      paidHours: 7.5,
      amount: 1500,
    })
    expect(demoShifts[3]).toMatchObject({
      date: '2026-09-09',
      time: '09:00–13:00',
      paidHours: 4,
      amount: 800,
    })
    const expected = fixture.summaries['2026-09-01:2026-09-30']
    expect(demoTotals.hours).toBe(Number(expected.total_paid_hours))
    expect(demoTotals.amount).toBe(Number(expected.estimated_pay))
    const svg = decodeURIComponent(scheduleImage.split(',')[1]!)
    for (const shift of demoShifts) {
      expect(svg).toContain(shift.date.slice(5))
      expect(svg).toContain(shift.time)
    }
    render(<ReviewerShowcase onExit={vi.fn()} />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveFocus()
    const table = screen.getByRole('table', { hidden: true })
    expect(within(table).getAllByRole('row', { hidden: true })).toHaveLength(8)
  })
  it('separates correction and confirmation, preserves state, refuses conflicts and writes, resets only on replay', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    const original = JSON.stringify(fixture)
    render(<ReviewerShowcase onExit={vi.fn()} />)
    go(/02 AI 覆核/)
    expect(screen.getByRole('img')).toHaveAttribute('src', scheduleImage)
    expect(screen.getByRole('button', { name: '模擬確認' })).toBeDisabled()
    go(/模擬補正為 13:00/)
    expect(screen.getByRole('status')).toHaveTextContent(
      '通過格式檢查，尚未人工確認',
    )
    go(/01 結果/)
    go(/02 AI 覆核/)
    expect(screen.getByRole('button', { name: '模擬確認' })).toBeEnabled()
    go(/^模擬確認$/)
    expect(screen.getByRole('status')).toHaveTextContent(
      '已確認，僅本次示範，不寫入資料庫',
    )
    go(/03 規章/)
    go(/^衝突版本$/)
    expect(screen.getByText('合成員工手冊 A')).toBeVisible()
    expect(screen.getByText('合成員工手冊 B')).toBeVisible()
    expect(screen.getByRole('status')).toHaveTextContent('拒絕回答')
    go(/04 助理/)
    go(/嘗試寫入要求/)
    expect(screen.getByRole('status')).toHaveTextContent(
      '未執行寫入，班表未變更',
    )
    go(/02 AI 覆核/)
    expect(screen.getByRole('status')).toHaveTextContent('已確認')
    go(/03 規章/)
    expect(screen.getByRole('button', { name: '衝突版本' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    go(/04 助理/)
    expect(
      screen.getByRole('button', { name: '嘗試寫入要求' }),
    ).toHaveAttribute('aria-pressed', 'true')
    go(/05 證據/)
    go(/重新體驗/)
    expect(screen.getByRole('heading', { level: 1 })).toHaveFocus()
    expect(document.querySelector('details')).not.toHaveAttribute('open')
    go(/02 AI 覆核/)
    expect(screen.getByRole('status')).toHaveTextContent('待覆核')
    go(/03 規章/)
    expect(
      screen.getByRole('button', { name: '單一有效版本' }),
    ).toHaveAttribute('aria-pressed', 'true')
    go(/04 助理/)
    expect(screen.getByRole('button', { name: '班表 × 規章' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(JSON.stringify(fixture)).toBe(original)
    expect(fetchSpy).not.toHaveBeenCalled()
  })
  it('supports previous, direct navigation and exit without production controls', () => {
    const onExit = vi.fn()
    render(<ReviewerShowcase onExit={onExit} />)
    go(/下一步/)
    go(/上一步/)
    expect(screen.getByRole('button', { name: '上一步' })).toBeDisabled()
    go(/05 證據/)
    expect(screen.getByRole('link', { name: 'RLS 整合測試' })).toHaveAttribute(
      'href',
      expect.stringContaining('test_migrations_and_rls.py'),
    )
    expect(
      screen.queryByRole('button', { name: '新增班次' }),
    ).not.toBeInTheDocument()
    expect(document.querySelector('input, video')).toBeNull()
    go(/返回首頁/)
    expect(onExit).toHaveBeenCalledOnce()
  })
})
