import { Activity, Clock, Scan } from 'lucide-react'
import type { StatusResponse } from '../../types/api'
import { formatNumber, formatUptime } from '../../utils/format'

interface Props {
  status: StatusResponse | null
  loading: boolean
}

export function ScannerStats({ status, loading }: Props) {
  const totals = status?.worker_totals ?? {}
  const scanned = totals.total_scanned ?? totals.scanned ?? 0
  const candidates = totals.candidates ?? 0
  const approved = totals.approved ?? 0

  const uptime = status?.uptime_seconds
  const cyclesPerHour =
    uptime && uptime > 0
      ? (((totals.scanned ?? 0) / uptime) * 3600).toFixed(1)
      : null

  const cacheHit =
    scanned > 0 ? `${(((scanned - (totals.errors ?? 0)) / scanned) * 100).toFixed(0)}%` : '—'

  const stats = [
    { icon: <Scan className="h-3.5 w-3.5" />, label: 'Instruments Scanned', value: formatNumber(scanned) },
    { icon: <Activity className="h-3.5 w-3.5" />, label: 'Candidates Found', value: formatNumber(candidates) },
    { icon: <Activity className="h-3.5 w-3.5 text-[#3fb950]" />, label: 'Approved', value: formatNumber(approved) },
    { icon: <Clock className="h-3.5 w-3.5" />, label: 'Cycles / hr', value: cyclesPerHour ?? '—' },
    { icon: <Activity className="h-3.5 w-3.5" />, label: 'Success Rate', value: cacheHit },
    { icon: <Clock className="h-3.5 w-3.5" />, label: 'Uptime', value: formatUptime(uptime) },
  ]

  return (
    <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-[#8b949e]">
        Scanner Stats
      </h3>
      {loading && !status ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#388bfd] border-t-transparent" />
        </div>
      ) : (
        <ul className="space-y-2.5">
          {stats.map((s) => (
            <li key={s.label} className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-xs text-[#8b949e]">
                {s.icon}
                {s.label}
              </span>
              <span className="font-mono text-xs font-semibold text-[#e6edf3]">{s.value}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
