import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  AssistantPanel,
  type AssistantClient,
} from '../src/features/assistant/AssistantPanel'

const range = { dateFrom: '2026-09-01', dateTo: '2026-09-07' }

describe('AssistantPanel', () => {
  afterEach(cleanup)

  it('renders hybrid facts, tool trace, and database citations', async () => {
    const client: AssistantClient = {
      queryAssistant: vi.fn().mockResolvedValue({
        answer: '最長連續工作 6 天，超過規章上限 5 天。',
        intent: 'hybrid',
        refused: false,
        citations: [
          {
            document_id: '00000000-0000-0000-0000-000000000101',
            chunk_id: '00000000-0000-0000-0000-000000000102',
            title: '合成員工手冊',
            page_number: 3,
            excerpt: '員工不得連續工作超過五天。',
          },
        ],
        schedule_facts: {
          date_from: range.dateFrom,
          date_to: range.dateTo,
          timezone: 'Asia/Taipei',
          currency: 'TWD',
          shift_count: 6,
          total_paid_hours: '42.0',
          estimated_pay: '8400.00',
          longest_consecutive_days: 6,
        },
        tools: [
          { name: 'schedule_summary', status: 'used' },
          { name: 'policy_retrieval', status: 'used' },
          { name: 'rule_evaluator', status: 'used' },
        ],
        prompt_version: 'hybrid_compliance_v1',
        model_name: 'synthetic-model',
      }),
    }
    render(<AssistantPanel client={client} range={range} />)

    fireEvent.change(screen.getByLabelText('問 ShiftMate'), {
      target: { value: '我的班表有違反連續工作規定嗎？' },
    })
    fireEvent.click(screen.getByRole('button', { name: '送出問題' }))

    expect(await screen.findByText('班表 × 規章')).toBeInTheDocument()
    expect(screen.getByText('42.0 小時')).toBeInTheDocument()
    expect(screen.getByText('規則比對 · 已使用')).toBeInTheDocument()
    expect(screen.getByText('合成員工手冊，第 3 頁')).toBeInTheDocument()
    expect(client.queryAssistant).toHaveBeenCalledWith(
      '我的班表有違反連續工作規定嗎？',
      range,
    )
  })

  it('shows bounded unsupported responses without invented evidence', async () => {
    const client: AssistantClient = {
      queryAssistant: vi.fn().mockResolvedValue({
        answer: '我目前只能回答班表、工時、預估薪資與已上傳規章相關問題。',
        intent: 'unsupported',
        refused: true,
        citations: [],
        schedule_facts: null,
        tools: [],
        prompt_version: null,
        model_name: null,
      }),
    }
    render(<AssistantPanel client={client} range={range} />)
    fireEvent.change(screen.getByLabelText('問 ShiftMate'), {
      target: { value: '今天天氣如何？' },
    })
    fireEvent.click(screen.getByRole('button', { name: '送出問題' }))

    expect(await screen.findByText('不支援')).toBeInTheDocument()
    expect(screen.getByText('資料不足')).toBeInTheDocument()
    expect(
      screen.queryByRole('list', { name: '引用來源' }),
    ).not.toBeInTheDocument()
  })
})
