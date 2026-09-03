export type ReviewerMetric = {
  label: string
  value: string
  note: string
}

export type ReviewerImportCandidate = {
  date: string
  time: string
  status: 'confirmed' | 'review'
  warning?: string
}

export type ReviewerEvidence = {
  label: string
  value: string
}

export const reviewerShowcase = {
  dashboard: {
    metrics: [
      { label: '總工時', value: '40', note: '小時' },
      { label: '預估薪資', value: 'NT$8,000', note: '有效期費率' },
      { label: '班次', value: '6', note: '筆合成資料' },
      { label: '最長連續工作', value: '2', note: '天' },
    ] satisfies ReviewerMetric[],
    overnight: '2026-09-03 · 22:00–06:00 · 扣除 30 分鐘休息',
  },
  importReview: {
    pipeline: [
      '合成班表影像',
      'Gemini structured output',
      '資料庫草稿',
      '人工確認',
      '班表',
    ],
    candidates: [
      { date: '09/02', time: '09:00–17:00', status: 'confirmed' },
      { date: '09/03', time: '22:00–06:00', status: 'confirmed' },
      {
        date: '09/09',
        time: '09:00–?',
        status: 'review',
        warning: '結束時間不清楚，禁止直接寫入',
      },
    ] satisfies ReviewerImportCandidate[],
  },
  rag: {
    question: '連續工作最多可以幾天？',
    answer:
      '合成員工手冊規定，連續工作不得超過 6 天；若檢索到衝突版本，系統會拒絕下結論。',
    citation: '2026 合成員工手冊，第 4 頁',
    excerpt: '員工連續工作日數不得超過六日，例外安排須經人工覆核。',
    refusal: '偵測到兩個版本的規則衝突，因此資料不足，未提供合規判定。',
  },
  assistant: {
    question: '我的班表有違反連續工作規定嗎？',
    route: 'hybrid · 班表 × 規章',
    answer:
      '目前最長連續工作為 2 天；引用規章門檻為 6 天。這是合成展示，不構成法律或人資判定。',
    facts: ['6 班', '40 小時', 'NT$8,000', '最長 2 天'],
    tools: ['班表摘要 · 已使用', '規章檢索 · 已使用', '規則比對 · 已使用'],
    writeQuestion: '請幫我刪除 9 月 3 日的夜班。',
    writeRefusal:
      '這個助理只有讀取工具，不能新增、修改或刪除已確認班次。請回到工作區由使用者明確操作。',
    writeTools: ['意圖路由 · write', '資料工具 · 未呼叫', '班表內容 · 未變更'],
  },
  platform: {
    evidence: [
      {
        label: 'Google Calendar',
        value: '最小 scope＋冪等同步；失敗時提供 ICS',
      },
      { label: 'MCP', value: '6 個 owner-scoped read-only tools' },
      {
        label: 'PostgreSQL',
        value: 'RLS owner isolation；runtime role 無 BYPASSRLS',
      },
      { label: 'GitHub → GCP', value: 'branch-restricted WIF；無 JSON key' },
      { label: 'Cloud Run', value: 'request-based · min 0 · max 1 · 512 MiB' },
      { label: 'Evaluation', value: 'OCR 9 · RAG 5 · routing 12 個合成案例' },
    ] satisfies ReviewerEvidence[],
  },
} as const

export const reviewerLinks = {
  repository: 'https://github.com/mieuxwei/shiftmate-web',
  openApi: '/docs',
  evaluations:
    'https://github.com/mieuxwei/shiftmate-web/blob/main/evals/reports/summary.md',
  video:
    'https://github.com/mieuxwei/shiftmate-web/releases/download/v1.0.0/shiftmate-demo.mp4',
} as const
