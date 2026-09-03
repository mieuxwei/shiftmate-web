import type { AnalyticsSummary, DateRange, PayRate, Shift } from '../api/types'
import type { WorkspaceClient } from '../features/workspace/Workspace'
import fixtureJson from './schedule-demo.json'

type DemoFixture = {
  profile: { display_name: string; timezone: string; currency: string }
  pay_rates: PayRate[]
  shifts: Shift[]
  summaries: Record<string, AnalyticsSummary>
}

export const demoFixture = fixtureJson as DemoFixture

function emptySummary(range: DateRange): AnalyticsSummary {
  return {
    date_from: range.dateFrom,
    date_to: range.dateTo,
    timezone: demoFixture.profile.timezone,
    currency: demoFixture.profile.currency,
    shift_count: 0,
    total_paid_hours: '0',
    estimated_pay: '0.00',
    shift_type_counts: {},
    weekly_hours: {},
    longest_consecutive_days: 0,
  }
}

class SyntheticDemoClient implements WorkspaceClient {
  listShifts(range: Partial<DateRange> = {}): Promise<Shift[]> {
    return Promise.resolve(
      demoFixture.shifts.filter(
        (shift) =>
          (!range.dateFrom || shift.work_date >= range.dateFrom) &&
          (!range.dateTo || shift.work_date <= range.dateTo),
      ),
    )
  }

  getAnalyticsSummary(range: DateRange): Promise<AnalyticsSummary> {
    return Promise.resolve(
      demoFixture.summaries[`${range.dateFrom}:${range.dateTo}`] ??
        emptySummary(range),
    )
  }

  listPayRates(): Promise<PayRate[]> {
    return Promise.resolve(demoFixture.pay_rates)
  }

  createShift(): Promise<Shift> {
    return Promise.reject(new Error('Synthetic demo is read-only'))
  }

  updateShift(): Promise<Shift> {
    return Promise.reject(new Error('Synthetic demo is read-only'))
  }

  deleteShift(): Promise<void> {
    return Promise.reject(new Error('Synthetic demo is read-only'))
  }

  createPayRate(): Promise<PayRate> {
    return Promise.reject(new Error('Synthetic demo is read-only'))
  }

  updatePayRate(): Promise<PayRate> {
    return Promise.reject(new Error('Synthetic demo is read-only'))
  }

  deletePayRate(): Promise<void> {
    return Promise.reject(new Error('Synthetic demo is read-only'))
  }
}

export const syntheticDemoClient: WorkspaceClient = new SyntheticDemoClient()
