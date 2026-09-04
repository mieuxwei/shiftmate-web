import fixture from './schedule-demo.json'

const rates: {
  hourly_rate: string
  effective_from: string
  effective_to: string | null
}[] = fixture.pay_rates
// Bounded presentation arithmetic, not the production payroll service.
const clock = (value: string) =>
  new Intl.DateTimeFormat('en-GB', {
    timeZone: fixture.profile.timezone,
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(new Date(value))
export const demoShifts = fixture.shifts.map((shift) => {
  const rate = rates.find(
    (item) =>
      item.effective_from <= shift.work_date &&
      (!item.effective_to || item.effective_to >= shift.work_date),
  )!
  const grossHours =
    (Date.parse(shift.end_at) - Date.parse(shift.start_at)) / 3_600_000
  const paidHours = grossHours - shift.break_minutes / 60
  return {
    date: shift.work_date,
    time: clock(shift.start_at) + '–' + clock(shift.end_at),
    breakMinutes: shift.break_minutes,
    grossHours,
    paidHours,
    rate: Number(rate.hourly_rate),
    amount: paidHours * Number(rate.hourly_rate),
  }
})
const dates = demoShifts
  .map((shift) => Date.parse(shift.date))
  .sort((a, b) => a - b)
let run = 0
let longest = 0
dates.forEach((date, index) => {
  run = index > 0 && date - dates[index - 1]! === 86_400_000 ? run + 1 : 1
  longest = Math.max(longest, run)
})
export const demoTotals = {
  hours: demoShifts.reduce((sum, shift) => sum + shift.paidHours, 0),
  amount: demoShifts.reduce((sum, shift) => sum + shift.amount, 0),
  count: demoShifts.length,
  longest,
}
export const money = (amount: number) => 'NT$' + amount.toLocaleString('en-US')

// Code-native synthetic input image; its rows share the result fixture.
export const scheduleImage =
  'data:image/svg+xml;charset=utf-8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="560" height="350" viewBox="0 0 560 350"><rect width="560" height="350" rx="14" fill="#f2f0e8"/><g font-family="sans-serif" fill="#163728"><text x="24" y="36" font-size="22" font-weight="700">SYNTHETIC SCHEDULE · 2026 / 09</text><text x="24" y="64" font-size="14">Asia/Taipei · TWD 200/hr · Not a real workplace</text><text x="24" y="104" font-size="15">DATE</text><text x="175" y="104" font-size="15">SHIFT</text><text x="390" y="104" font-size="15">BREAK (min)</text>' +
      demoShifts
        .map(
          (shift, index) =>
            '<path d="M24 ' +
            (116 + index * 35) +
            'H536" stroke="#bcc9c0"/><text x="24" y="' +
            (140 + index * 35) +
            '" font-size="17">' +
            shift.date.slice(5) +
            '</text><text x="175" y="' +
            (140 + index * 35) +
            '" font-size="17">' +
            shift.time +
            '</text><text x="420" y="' +
            (140 + index * 35) +
            '" font-size="17">' +
            shift.breakMinutes +
            '</text>',
        )
        .join('') +
      '</g></svg>',
  )

export const policySources = [
  {
    version: '版本 A · 2026-09',
    name: '合成員工手冊 A',
    source: '示範文件 A，第 4 頁 §2',
    excerpt: '員工連續工作日數不得超過六日，例外安排須經人工覆核。',
  },
  {
    version: '版本 B · 2026-09',
    name: '合成員工手冊 B',
    source: '示範文件 B，第 2 頁 §1',
    excerpt: '員工連續工作日數不得超過四日，例外安排須經人工覆核。',
  },
] as const
export const reviewerLinks = {
  repository: 'https://github.com/mieuxwei/shiftmate-web',
  evaluations:
    'https://github.com/mieuxwei/shiftmate-web/blob/main/evals/reports/summary.md',
} as const
export const repoFile = (path: string) =>
  reviewerLinks.repository + '/blob/main/' + path
