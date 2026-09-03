import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ReviewerShowcase } from '../src/features/reviewer/ReviewerShowcase'

describe('ReviewerShowcase', () => {
  afterEach(cleanup)

  it('walks through all five synthetic evidence cases without network calls', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')

    render(<ReviewerShowcase onExit={vi.fn()} />)

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      '先看結果',
    )
    expect(screen.getByText('NT$8,000')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'AI 只建立草稿',
    )
    expect(screen.getByText('結束時間不清楚，禁止直接寫入')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      '可追溯的頁面引用',
    )
    expect(screen.getByText(/2026 合成員工手冊/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'LangGraph',
    )
    expect(screen.getByText('班表摘要 · 已使用')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      '安全、整合與部署',
    )
    expect(screen.getByText(/branch-restricted WIF/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '重新導覽' })).toBeInTheDocument()
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('supports direct navigation, previous, replay and exit', () => {
    const onExit = vi.fn()
    render(<ReviewerShowcase onExit={onExit} />)

    fireEvent.click(screen.getByRole('button', { name: /05 系統證據/ }))
    expect(screen.getByText('第 5 步，共 5 步')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '上一步' }))
    expect(screen.getByText('第 4 步，共 5 步')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '返回產品首頁' }))
    expect(onExit).toHaveBeenCalledOnce()

    fireEvent.click(screen.getByRole('link', { name: /ShiftMate Web/ }))
    expect(screen.getByText('第 1 步，共 5 步')).toBeInTheDocument()
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
