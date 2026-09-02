import { describe, expect, it } from 'vitest'

import {
  enumerateDates,
  moveAnchor,
  rangeFor,
} from '../src/features/schedule/dateRange'

describe('schedule date ranges', () => {
  it('builds inclusive month ranges including leap years', () => {
    expect(rangeFor('month', '2028-02-14')).toEqual({
      dateFrom: '2028-02-01',
      dateTo: '2028-02-29',
    })
  })

  it('builds Monday-to-Sunday week ranges', () => {
    expect(rangeFor('week', '2026-09-02')).toEqual({
      dateFrom: '2026-08-31',
      dateTo: '2026-09-06',
    })
  })

  it('moves month and week anchors deterministically', () => {
    expect(moveAnchor('month', '2026-09-30', 1)).toBe('2026-10-30')
    expect(moveAnchor('week', '2026-09-02', -1)).toBe('2026-08-26')
  })

  it('enumerates both endpoints', () => {
    expect(
      enumerateDates({ dateFrom: '2026-09-01', dateTo: '2026-09-03' }),
    ).toEqual(['2026-09-01', '2026-09-02', '2026-09-03'])
  })
})
