import { Bot, RefreshCw, Wifi } from 'lucide-react'
import { useTranslation } from '../../i18n/I18nProvider'
import type { Opportunity, StatsResponse, StatusResponse } from '../../types/api'
import { LanguageToggle } from './LanguageToggle'

interface TopbarProps {
  opportunities: Opportunity[]
  stats: StatsResponse | null
  status: StatusResponse | null
  countdown: number
  loading: boolean
  onRefresh: () => void
  alertThreshold?: number
}

export function Topbar({
  opportunities,
  stats,
  status,
  countdown,
  loading,
  onRefresh,
  alertThreshold = 65,
}: TopbarProps) {
  const { t } = useTranslation()
  const highScore = opportunities.filter((o) => o.total_score >= 85).length
  const scanned = status?.worker_totals?.total_scanned ?? status?.worker_totals?.scanned ?? 0
  const totalMarkets =
    scanned > 0 ? scanned : stats?.total_today ?? opportunities.length

  const botRunning = status?.scanner_running ?? false

  return (
    <header className="flex flex-wrap items-center gap-4 border-b border-[#30363d] bg-[#161b22] px-6 py-3">
      <div className="flex items-center gap-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#3fb950] opacity-60" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#3fb950]" />
        </span>
        <span className="text-xs font-bold tracking-widest text-[#3fb950]">{t('common.live')}</span>
      </div>

      <div className="h-4 w-px bg-[#30363d]" />

      <Stat label={t('topbar.marketsScanned')} value={String(totalMarkets)} />
      <Stat label={t('topbar.opportunities')} value={String(opportunities.length)} highlight />
      <Stat label={t('topbar.highScore')} value={String(highScore)} color="#3fb950" />
      <Stat label={t('topbar.alertThreshold')} value={String(alertThreshold)} color="#d29922" />

      <div className="ml-auto flex items-center gap-3">
        <div
          className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
            botRunning
              ? 'bg-[#3fb950]/15 text-[#3fb950]'
              : 'bg-[#f85149]/15 text-[#f85149]'
          }`}
        >
          <Bot className="h-3.5 w-3.5" />
          {botRunning ? t('topbar.botActive') : t('topbar.botOffline')}
        </div>

        <div className="flex items-center gap-1.5 text-xs text-[#8b949e]">
          <Wifi className="h-3.5 w-3.5" />
          <span className="font-mono">{countdown}s</span>
        </div>

        <LanguageToggle />

        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-[#30363d] bg-[#21262d] px-3 py-1.5 text-xs text-[#e6edf3] hover:bg-[#30363d] disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </button>
      </div>
    </header>
  )
}

function Stat({
  label,
  value,
  highlight,
  color,
}: {
  label: string
  value: string
  highlight?: boolean
  color?: string
}) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wide text-[#8b949e]">{label}</span>
      <span
        className={`font-mono text-sm font-semibold ${highlight ? 'text-[#388bfd]' : ''}`}
        style={color ? { color } : undefined}
      >
        {value}
      </span>
    </div>
  )
}
