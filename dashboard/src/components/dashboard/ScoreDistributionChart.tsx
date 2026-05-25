import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { StatsResponse } from '../../types/api'

interface Props {
  stats: StatsResponse | null
  loading: boolean
}

const COLORS = {
  excellent: '#3fb950',
  good: '#d29922',
  watch: '#388bfd',
}

export function ScoreDistributionChart({ stats, loading }: Props) {
  const data = stats
    ? [
        { name: 'Excellent', value: stats.by_grade.excellent, color: COLORS.excellent },
        { name: 'Good', value: stats.by_grade.good, color: COLORS.good },
        { name: 'Watch', value: stats.by_grade.watch, color: COLORS.watch },
      ].filter((d) => d.value > 0)
    : []

  const total = data.reduce((s, d) => s + d.value, 0)

  return (
    <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-[#8b949e]">
        Score Distribution
      </h3>
      {loading && !stats ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#388bfd] border-t-transparent" />
        </div>
      ) : total === 0 ? (
        <div className="flex h-40 flex-col items-center justify-center text-center">
          <p className="text-sm text-[#484f58]">No scored opportunities today</p>
        </div>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={70}
                paddingAngle={3}
                dataKey="value"
              >
                {data.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} stroke="none" />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: '#21262d',
                  border: '1px solid #30363d',
                  borderRadius: 8,
                  fontSize: 12,
                }}
                itemStyle={{ color: '#e6edf3' }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-2 flex justify-center gap-4">
            {data.map((d) => (
              <div key={d.name} className="flex items-center gap-1.5 text-[10px]">
                <span className="h-2 w-2 rounded-full" style={{ background: d.color }} />
                <span className="text-[#8b949e]">{d.name}</span>
                <span className="font-mono font-bold text-[#e6edf3]">{d.value}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
