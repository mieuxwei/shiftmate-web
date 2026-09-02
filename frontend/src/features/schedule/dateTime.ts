function partsInTimeZone(value: Date, timezone: string) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(value)
  return Object.fromEntries(parts.map((part) => [part.type, part.value]))
}

export function isoToLocalInput(value: string, timezone: string): string {
  const parts = partsInTimeZone(new Date(value), timezone)
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`
}

export function localInputToIso(value: string, timezone: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value)
  if (!match) throw new Error('Invalid local date-time')
  const [, year, month, day, hour, minute] = match
  const desired = Date.UTC(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
  )
  let guess = desired

  for (let iteration = 0; iteration < 3; iteration += 1) {
    const parts = partsInTimeZone(new Date(guess), timezone)
    const represented = Date.UTC(
      Number(parts.year),
      Number(parts.month) - 1,
      Number(parts.day),
      Number(parts.hour),
      Number(parts.minute),
      Number(parts.second),
    )
    guess -= represented - desired
  }

  const result = new Date(guess)
  if (isoToLocalInput(result.toISOString(), timezone) !== value) {
    throw new Error('This local time does not exist in the configured timezone')
  }
  return result.toISOString()
}
