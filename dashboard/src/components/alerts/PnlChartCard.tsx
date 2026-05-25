import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useTranslation } from '../../i18n/I18nProvider'
import type { AlertStatsResponse } from '../../types/api'

interface PnlChartCardProps {
  stats: AlertStatsResponse | null
  className?: string
}

export function PnlChartCard({ stats, className = '' }: PnlChartCardProps) {
  const { t } = useTranslation()
  const data = stats?.pnl_by_day ?? []
  const lastCumulative = data.length ? data[data.length - 1].cumulative_pnl : 0
  const chartColor = lastCumulative >= 0 ? '#3fb950' : '#f85149'

  return (
    <div
      className={`flex flex-col rounded-lg border border-[#30363d] bg-[#161b22] p-4 ${className}`}
    >
      <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-[#8b949e]">
        {t('alerts.cumulativePnl')}
      </h3>
      {!data.length ? (
        <div className="flex flex-1 min-h-[220px] items-center justify-center text-center text-sm text-[#484f58] px-4">
          {t('alerts.pnlChartEmpty')}
        </div>
      ) : (
        <div className="min-h-[220px] flex-1">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid stroke="#21262d" strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#8b949e', fontSize: 10 }}
                tickFormatter={(v: string) => v.slice(5)}
              />
              <YAxis tick={{ fill: '#8b949e', fontSize: 10 }} unit="%" />
              <Tooltip
                contentStyle={{
                  background: '#21262d',
                  border: '1px solid #30363d',
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(value) => [`${Number(value ?? 0).toFixed(2)}%`, 'Cumulative']}
              />
              <Line
                type="monotone"
                dataKey="cumulative_pnl"
                stroke={chartColor}
                strokeWidth={2}
                dot={{ fill: chartColor, r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
