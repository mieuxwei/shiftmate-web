export type ShiftSource = 'manual' | 'import' | 'calendar'

export type Shift = {
  id: string
  work_date: string
  start_at: string
  end_at: string
  break_minutes: number
  shift_type: string
  notes: string | null
  source: ShiftSource
  created_at: string
  updated_at: string
}

export type ShiftCreate = {
  start_at: string
  end_at: string
  break_minutes?: number
  shift_type: string
  notes?: string | null
}

export type ShiftUpdate = Partial<ShiftCreate>

export type PayRate = {
  id: string
  hourly_rate: string
  effective_from: string
  effective_to: string | null
  created_at: string
  updated_at: string
}

export type PayRateCreate = {
  hourly_rate: string
  effective_from: string
  effective_to?: string | null
}

export type PayRateUpdate = Partial<PayRateCreate>

export type AnalyticsSummary = {
  date_from: string
  date_to: string
  timezone: string
  currency: string
  shift_count: number
  total_paid_hours: string
  estimated_pay: string
  shift_type_counts: Record<string, number>
  weekly_hours: Record<string, string>
  longest_consecutive_days: number
}

export type DateRange = {
  dateFrom: string
  dateTo: string
}

export type ImportStatus =
  'uploaded' | 'extracting' | 'review' | 'committed' | 'failed' | 'expired'

export type ImportItem = {
  id: string
  work_date: string | null
  start_at: string | null
  end_at: string | null
  break_minutes: number | null
  shift_type: string | null
  notes: string | null
  validation_status: 'pending' | 'valid' | 'invalid'
  needs_review: boolean
  warnings: string[]
  confirmed: boolean
  committed_shift_id: string | null
}

export type ShiftImport = {
  id: string
  filename: string
  media_type: 'image/jpeg' | 'image/png' | 'application/pdf'
  status: ImportStatus
  model_name: string | null
  prompt_version: string | null
  error_code: string | null
  created_at: string
  updated_at: string
  items: ImportItem[]
}

export type ImportItemUpdate = {
  work_date?: string | null
  start_time?: string | null
  end_time?: string | null
  crosses_midnight?: boolean
  break_minutes?: number | null
  shift_type?: string | null
  notes?: string | null
  confirmed?: boolean
}

export type ImportCommit = {
  import_id: string
  status: 'committed'
  created_shift_ids: string[]
}

export type PolicyStatus = 'uploaded' | 'indexing' | 'ready' | 'failed'

export type PolicyDocument = {
  id: string
  title: string
  filename: string
  status: PolicyStatus
  page_count: number | null
  error_code: string | null
  created_at: string
  updated_at: string
}

export type PolicyUpload = {
  document: PolicyDocument
  duplicate: boolean
}

export type PolicyCitation = {
  document_id: string
  chunk_id: string
  title: string
  page_number: number
  excerpt: string
}

export type PolicyAnswer = {
  answer: string
  refused: boolean
  citations: PolicyCitation[]
  prompt_version: string
  model_name: string | null
}

export type AssistantIntent = 'schedule' | 'policy' | 'hybrid' | 'unsupported'

export type AssistantScheduleFacts = {
  date_from: string
  date_to: string
  timezone: string
  currency: string
  shift_count: number
  total_paid_hours: string
  estimated_pay: string
  longest_consecutive_days: number
}

export type AssistantToolTrace = {
  name: 'schedule_summary' | 'policy_retrieval' | 'rule_evaluator'
  status: 'used' | 'insufficient'
}

export type AssistantAnswer = {
  answer: string
  intent: AssistantIntent
  refused: boolean
  citations: PolicyCitation[]
  schedule_facts: AssistantScheduleFacts | null
  tools: AssistantToolTrace[]
  prompt_version: string | null
  model_name: string | null
}
