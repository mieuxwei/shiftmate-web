import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ReviewerShowcase } from '../src/features/reviewer/ReviewerShowcase'

describe('ReviewerShowcase', () => {
  afterEach(cleanup)

  it('walks through all five synthetic evidence cases without network calls', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')

    render(<ReviewerShowcase onExit={vi.fn()} />)

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      '先確認班表',
    )
    expect(screen.getByText('NT$8,000')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'AI 提案',
    )
    expect(screen.getByText('結束時間不清楚，禁止直接寫入')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      '回到原文',
    )
    expect(screen.getByText(/2026 合成員工手冊/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      '班表事實與規章證據',
    )
    expect(screen.getByText('班表摘要 · 已使用')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      '安全邊界',
    )
    expect(screen.getByText(/branch-restricted WIF/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '重新導覽' })).toBeInTheDocument()
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('supports direct navigation, previous, replay and exit', () => {
    const onExit = vi.fn()
    render(<ReviewerShowcase onExit={onExit} />)

    fireEvent.click(screen.getByRole('button', { name: /05 證據/ }))
    expect(screen.getByText('第 5 步，共 5 步')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '上一步' }))
    expect(screen.getByText('第 4 步，共 5 步')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '返回首頁' }))
    expect(onExit).toHaveBeenCalledOnce()

    fireEvent.click(screen.getByRole('link', { name: /ShiftMate Web/ }))
    expect(screen.getByText('第 1 步，共 5 步')).toBeInTheDocument()
  })

  it('lets a visitor exercise correction, conflict, and write-refusal states', () => {
    render(<ReviewerShowcase onExit={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: /02 AI 覆核/ }))
    fireEvent.click(screen.getByRole('button', { name: '模擬人工補正 17:00' }))
    expect(screen.getByRole('status')).toHaveTextContent('通過驗證')
    expect(screen.getByText('可確認')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /03 規章/ }))
    fireEvent.click(screen.getByRole('button', { name: '衝突版本' }))
    expect(screen.getByRole('status')).toHaveTextContent('未提供合規判定')
    expect(screen.queryByText(/2026 合成員工手冊/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /04 助理/ }))
    fireEvent.click(screen.getByRole('button', { name: '嘗試寫入要求' }))
    expect(screen.getByText(/只有讀取工具/)).toBeInTheDocument()
    expect(screen.getByText('資料工具 · 未呼叫')).toBeInTheDocument()
  })

  it('never exposes production write controls', () => {
    render(<ReviewerShowcase onExit={vi.fn()} />)

    expect(
      screen.queryByRole('button', { name: '新增班次' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: '寫入已確認班次' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: '同步目前期間' }),
    ).not.toBeInTheDocument()
  })
})
