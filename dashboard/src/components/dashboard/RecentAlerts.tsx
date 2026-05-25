import { Bell } from 'lucide-react'
import type { Opportunity } from '../../types/api'
import { gradeColor, gradeLabel } from '../../utils/colors'
import { formatRelativeTime, pairLabel } from '../../utils/format'

interface Props {
  opportunities: Opportunity[]
}

export function RecentAlerts({ opportunities }: Props) {
  const recent = [...opportunities]
    .sort((a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime())
    .slice(0, 3)

  return (
    <div className="border-t border-[#30363d] bg-[#161b22] px-6 py-3">
      <div className="flex items-center gap-2 mb-2">
        <Bell className="h-3.5 w-3.5 text-[#d29922]" />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[#8b949e]">
          Recent Alerts
        </span>
      </div>
      {recent.length === 0 ? (
        <p className="text-xs text-[#484f58]">No alerts yet — waiting for approved opportunities</p>
      ) : (
        <div className="flex flex-wrap gap-3">
          {recent.map((item) => {
            const grade = gradeLabel(item.grade, item.total_score)
            const color = gradeColor(item.grade, item.total_score)
            return (
              <div
                key={item.id}
                className="flex items-center gap-3 rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2"
              >
                <span className="font-mono text-xs font-bold text-[#e6edf3]">
                  {pairLabel(item.symbol)}
                </span>
                <span
                  className="font-mono text-xs font-bold"
                  style={{ color }}
                >
                  {item.total_score}
                </span>
                <span className="text-[10px] text-[#8b949e]">{grade}</span>
                <span
                  className={`text-[10px] font-bold ${
                    item.strategy === 'FUNDING' ? 'text-[#f85149]' : 'text-[#388bfd]'
                  }`}
                >
                  {item.strategy}
                </span>
                <span className="text-[10px] text-[#484f58]">
                  {formatRelativeTime(item.detected_at)}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
