import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react'
import type { HealthResponse } from '../../types/api'

interface Props {
  health: HealthResponse | null
  loading: boolean
}

const CHECK_LABELS: Record<string, string> = {
  database: 'Database',
  redis: 'Redis',
  scanner: 'Scanner Worker',
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'ok') return <CheckCircle2 className="h-3.5 w-3.5 text-[#3fb950]" />
  if (status === 'degraded') return <AlertTriangle className="h-3.5 w-3.5 text-[#d29922]" />
  return <XCircle className="h-3.5 w-3.5 text-[#f85149]" />
}

function statusColor(status: string): string {
  if (status === 'ok') return '#3fb950'
  if (status === 'degraded') return '#d29922'
  return '#f85149'
}

export function SystemStatus({ health, loading }: Props) {
  const checks = health ? Object.entries(health.checks) : []

  return (
    <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-[#8b949e]">
          System Status
        </h3>
        {health && (
          <span
            className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase"
            style={{
              color: statusColor(health.status),
              backgroundColor: statusColor(health.status) + '22',
            }}
          >
            {health.status}
          </span>
        )}
      </div>
      {loading && !health ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#388bfd] border-t-transparent" />
        </div>
      ) : !health ? (
        <p className="text-xs text-[#484f58]">Health data unavailable</p>
      ) : (
        <ul className="space-y-2">
          {checks.map(([key, check]) => (
            <li key={key} className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-xs text-[#8b949e]">
                <StatusIcon status={check.status} />
                {CHECK_LABELS[key] ?? key}
              </span>
              <span className="font-mono text-[10px]" style={{ color: statusColor(check.status) }}>
                {check.latency_ms.toFixed(0)}ms
              </span>
            </li>
          ))}
          <li className="flex items-center justify-between border-t border-[#21262d] pt-2">
            <span className="text-xs text-[#8b949e]">API Version</span>
            <span className="font-mono text-[10px] text-[#e6edf3]">{health.version}</span>
          </li>
          <li className="flex items-center justify-between">
            <span className="text-xs text-[#8b949e]">Environment</span>
            <span className="font-mono text-[10px] text-[#e6edf3]">{health.env}</span>
          </li>
        </ul>
      )}
    </div>
  )
}
