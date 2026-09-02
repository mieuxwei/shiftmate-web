import { describe, expect, it } from 'vitest'

import {
  isoToLocalInput,
  localInputToIso,
} from '../src/features/schedule/dateTime'

describe('schedule date-time conversion', () => {
  it('converts Asia/Taipei wall time to UTC', () => {
    expect(localInputToIso('2026-09-02T09:00', 'Asia/Taipei')).toBe(
      '2026-09-02T01:00:00.000Z',
    )
  })

  it('round-trips a timezone-aware input value', () => {
    const iso = localInputToIso('2026-11-10T22:30', 'America/New_York')
    expect(isoToLocalInput(iso, 'America/New_York')).toBe('2026-11-10T22:30')
  })

  it('rejects a nonexistent daylight-saving wall time', () => {
    expect(() =>
      localInputToIso('2026-03-08T02:30', 'America/New_York'),
    ).toThrow('does not exist')
  })
})
