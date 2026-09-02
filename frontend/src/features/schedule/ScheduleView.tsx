import type { DateRange, Shift } from '../../api/types'
import { enumerateDates, type ScheduleViewMode } from './dateRange'

type ScheduleViewProps = {
  mode: ScheduleViewMode
  range: DateRange
  shifts: Shift[]
  timezone: string
}

const weekdayFormatter = new Intl.DateTimeFormat('zh-TW', {
  weekday: 'short',
})

function dateAtNoon(value: string): Date {
  return new Date(`${value}T12:00:00`)
}

function shiftTime(value: string, timezone: string): string {
  return new Intl.DateTimeFormat('zh-TW', {
    timeZone: timezone,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

export function ScheduleView({
  mode,
  range,
  shifts,
  timezone,
}: ScheduleViewProps) {
  const shiftsByDate = new Map<string, Shift[]>()
  for (const shift of shifts) {
    const existing = shiftsByDate.get(shift.work_date) ?? []
    existing.push(shift)
    shiftsByDate.set(shift.work_date, existing)
  }
  const dates = enumerateDates(range)
  const firstDate = dateAtNoon(range.dateFrom)
  const leadingCells = mode === 'month' ? (firstDate.getDay() + 6) % 7 : 0

  return (
    <section className="schedule" aria-labelledby="schedule-title">
      <div className="section-heading">
        <div>
          <p className="section-kicker">Schedule</p>
          <h2 id="schedule-title">{mode === 'month' ? '月班表' : '週班表'}</h2>
        </div>
        <p>{shifts.length} 筆班次</p>
      </div>

      <div className={`schedule-grid schedule-grid--${mode}`}>
        {mode === 'month' &&
          Array.from({ length: leadingCells }, (_, index) => (
            <span
              className="schedule-day schedule-day--blank"
              key={`blank-${index}`}
            />
          ))}
        {dates.map((dateValue) => {
          const dayShifts = shiftsByDate.get(dateValue) ?? []
          const date = dateAtNoon(dateValue)
          return (
            <article className="schedule-day" key={dateValue}>
              <header>
                <span>{weekdayFormatter.format(date)}</span>
                <strong>{date.getDate()}</strong>
              </header>
              <div className="schedule-day__shifts">
                {dayShifts.map((shift) => (
                  <div className="shift-chip" key={shift.id}>
                    <strong>{shift.shift_type}</strong>
                    <span>
                      {shiftTime(shift.start_at, timezone)}–
                      {shiftTime(shift.end_at, timezone)}
                    </span>
                  </div>
                ))}
                {dayShifts.length === 0 && <span className="no-shift">休</span>}
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
