import type { DateRange } from '../../api/types'

export type ScheduleViewMode = 'month' | 'week'

function parseDate(value: string): Date {
  const parts = value.split('-')
  if (parts.length !== 3) throw new Error('Invalid date value')
  const [yearPart, monthPart, dayPart] = parts as [string, string, string]
  const year = Number(yearPart)
  const month = Number(monthPart)
  const day = Number(dayPart)
  return new Date(year, month - 1, day, 12)
}

export function toDateValue(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function todayValue(now = new Date()): string {
  return toDateValue(now)
}

export function rangeFor(
  mode: ScheduleViewMode,
  anchorValue: string,
): DateRange {
  const anchor = parseDate(anchorValue)
  if (mode === 'month') {
    return {
      dateFrom: toDateValue(
        new Date(anchor.getFullYear(), anchor.getMonth(), 1, 12),
      ),
      dateTo: toDateValue(
        new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0, 12),
      ),
    }
  }

  const mondayOffset = (anchor.getDay() + 6) % 7
  const monday = new Date(anchor)
  monday.setDate(anchor.getDate() - mondayOffset)
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  return { dateFrom: toDateValue(monday), dateTo: toDateValue(sunday) }
}

export function moveAnchor(
  mode: ScheduleViewMode,
  anchorValue: string,
  direction: -1 | 1,
): string {
  const anchor = parseDate(anchorValue)
  if (mode === 'month') anchor.setMonth(anchor.getMonth() + direction)
  else anchor.setDate(anchor.getDate() + direction * 7)
  return toDateValue(anchor)
}

export function enumerateDates(range: DateRange): string[] {
  const cursor = parseDate(range.dateFrom)
  const end = parseDate(range.dateTo)
  const dates: string[] = []
  while (cursor <= end) {
    dates.push(toDateValue(cursor))
    cursor.setDate(cursor.getDate() + 1)
  }
  return dates
}

export function periodLabel(mode: ScheduleViewMode, range: DateRange): string {
  const start = parseDate(range.dateFrom)
  const end = parseDate(range.dateTo)
  const monthFormatter = new Intl.DateTimeFormat('zh-TW', {
    year: 'numeric',
    month: 'long',
  })
  if (mode === 'month') return monthFormatter.format(start)

  const dayFormatter = new Intl.DateTimeFormat('zh-TW', {
    month: 'numeric',
    day: 'numeric',
  })
  return `${start.getFullYear()} · ${dayFormatter.format(start)} – ${dayFormatter.format(end)}`
}
