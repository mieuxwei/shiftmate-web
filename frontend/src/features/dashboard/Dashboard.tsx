import type { AnalyticsSummary } from '../../api/types'

type DashboardProps = {
  summary: AnalyticsSummary
}

function numberValue(value: string): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function formatCurrency(value: string, currency: string): string {
  try {
    return new Intl.NumberFormat('zh-TW', {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(numberValue(value))
  } catch {
    return `${currency} ${value}`
  }
}

export function Dashboard({ summary }: DashboardProps) {
  const shiftTypes = Object.entries(summary.shift_type_counts)
  const weeklyHours = Object.entries(summary.weekly_hours)
  const maxTypeCount = Math.max(1, ...shiftTypes.map(([, count]) => count))
  const maxWeeklyHours = Math.max(
    1,
    ...weeklyHours.map(([, hours]) => numberValue(hours)),
  )

  return (
    <section className="dashboard" aria-labelledby="dashboard-title">
      <div className="section-heading">
        <div>
          <p className="section-kicker">Dashboard</p>
          <h2 id="dashboard-title">期間摘要</h2>
        </div>
        <p>{summary.timezone}</p>
      </div>

      <div className="metric-grid">
        <article>
          <span>總工時</span>
          <strong>{summary.total_paid_hours}</strong>
          <small>小時</small>
        </article>
        <article>
          <span>預估薪資</span>
          <strong>
            {formatCurrency(summary.estimated_pay, summary.currency)}
          </strong>
          <small>依有效期費率計算</small>
        </article>
        <article>
          <span>班次</span>
          <strong>{summary.shift_count}</strong>
          <small>筆</small>
        </article>
        <article>
          <span>最長連續工作</span>
          <strong>{summary.longest_consecutive_days}</strong>
          <small>天</small>
        </article>
      </div>

      {summary.shift_count === 0 ? (
        <p className="workspace-empty">這個期間還沒有班次。</p>
      ) : (
        <div className="chart-grid">
          <article>
            <h3>班別分布</h3>
            <div className="bar-chart" role="img" aria-label="班別分布圖">
              {shiftTypes.map(([shiftType, count]) => (
                <div className="bar-row" key={shiftType}>
                  <span>{shiftType}</span>
                  <div>
                    <i style={{ width: `${(count / maxTypeCount) * 100}%` }} />
                  </div>
                  <strong>{count}</strong>
                </div>
              ))}
            </div>
          </article>

          <article>
            <h3>每週工時趨勢</h3>
            <div className="bar-chart" role="img" aria-label="每週工時趨勢圖">
              {weeklyHours.map(([weekStart, hours]) => (
                <div className="bar-row" key={weekStart}>
                  <span>{weekStart.slice(5)}</span>
                  <div>
                    <i
                      style={{
                        width: `${(numberValue(hours) / maxWeeklyHours) * 100}%`,
                      }}
                    />
                  </div>
                  <strong>{hours}h</strong>
                </div>
              ))}
            </div>
          </article>
        </div>
      )}

      <div className="integration-status" aria-label="整合狀態">
        <span>最近匯入：M4 啟用</span>
        <span>Calendar 同步：M7 啟用</span>
      </div>
      <p className="calculation-note">
        工時與預估薪資由後端 deterministic service
        計算，僅供作品示範，不構成薪資或人資建議。
      </p>
    </section>
  )
}
