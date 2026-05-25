import { Activity, RefreshCw, TrendingDown, TrendingUp, Trophy } from 'lucide-react'
import { useState } from 'react'
import { CompactStatCard } from '../components/alerts/CompactStatCard'
import { PerformancePanels } from '../components/alerts/PerformancePanels'
import type { StrategyFilterKey, TierFilterKey } from '../components/alerts/PerformancePanels'
import { PnlChartCard } from '../components/alerts/PnlChartCard'
import { TradeFilterBar } from '../components/alerts/TradeFilterBar'
import { TradesTable } from '../components/alerts/TradesTable'
import { useAlerts, type StatusFilterKey } from '../hooks/useAlerts'
import { useTranslation } from '../i18n/I18nProvider'
import { DEFAULT_TIME_RANGE, type TimeRangeValue } from '../utils/timeRange'
import { formatPctColored } from '../utils/format'

type DirectionFilter = 'all' | 'LONG' | 'SHORT'

export function AlertsPage() {
  const { t } = useTranslation()
  const [statusFilter, setStatusFilter] = useState<StatusFilterKey>('all')
  const [strategyFilter, setStrategyFilter] = useState<StrategyFilterKey>('all')
  const [tierFilter, setTierFilter] = useState<TierFilterKey>('all')
  const [directionFilter, setDirectionFilter] = useState<DirectionFilter>('all')
  const [timeRange, setTimeRange] = useState<TimeRangeValue>(DEFAULT_TIME_RANGE)
  const [symbolSearch, setSymbolSearch] = useState('')

  const { items, stats, statusCounts, opportunityMap, loading, error, refresh } = useAlerts({
    status: statusFilter,
    strategy: strategyFilter,
    tier: tierFilter,
    direction: directionFilter,
    timeRange,
    symbolSearch,
  })

  const bestPnl = stats?.best_trade ? formatPctColored(stats.best_trade.pnl_pct) : null

  return (
    <div className="space-y-3 p-4 sm:p-5">
      {/* Page header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-[#388bfd]" />
          <h1 className="text-lg font-semibold text-[#e6edf3]">{t('alerts.title')}</h1>
        </div>
        <div className="flex items-center gap-2 text-xs text-[#8b949e]">
          <span>{t('common.autoRefresh')}</span>
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-[#30363d] bg-[#21262d] px-3 py-1.5 text-[#e6edf3] hover:bg-[#30363d] disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            {t('common.refresh')}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-[#f85149]/30 bg-[#f85149]/10 px-4 py-3 text-sm text-[#f85149]">
          {error}
        </div>
      )}

      {/* Section 1: Top stats */}
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        <CompactStatCard
          label={t('alerts.totalTrades')}
          value={String(stats?.total_trades ?? 0)}
          sub={
            stats
              ? t('alerts.runningSummary', {
                  running: stats.running,
                  wins: stats.wins,
                  losses: stats.losses,
                  expired: stats.expired,
                })
              : undefined
          }
          icon={<Activity className="h-3.5 w-3.5 text-[#388bfd]" />}
        />
        <CompactStatCard
          label={t('alerts.winRate')}
          value={stats ? `${stats.win_rate.toFixed(1)}%` : '—'}
          sub={t('alerts.closedTrades')}
          color="#3fb950"
          icon={<TrendingUp className="h-3.5 w-3.5 text-[#3fb950]" />}
        />
        <CompactStatCard
          label={t('alerts.avgPnl')}
          value={stats ? formatPctColored(stats.avg_pnl).text : '—'}
          color={formatPctColored(stats?.avg_pnl).color}
          icon={<TrendingDown className="h-3.5 w-3.5 text-[#d29922]" />}
        />
        <CompactStatCard
          label={t('alerts.bestTrade')}
          value={stats?.best_trade ? stats.best_trade.symbol.split('-')[0] : '—'}
          sub={bestPnl ? `${bestPnl.text} P&L` : t('alerts.noClosedTrades')}
          color={bestPnl?.color}
          icon={<Trophy className="h-3.5 w-3.5 text-[#d29922]" />}
        />
      </div>

      {/* Section 2: Analytics */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[35%_1fr] lg:items-stretch">
        <PerformancePanels
          stats={stats}
          strategyFilter={strategyFilter}
          tierFilter={tierFilter}
          onStrategyFilter={setStrategyFilter}
          onTierFilter={setTierFilter}
        />
        <PnlChartCard stats={stats} className="min-h-[280px] lg:min-h-0 lg:h-full" />
      </div>

      {/* Section 3: Confirmation stats */}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <CompactStatCard
          compact
          label={t('alerts.confirmationRate')}
          value={stats ? `${stats.confirmation_rate.toFixed(1)}%` : '—'}
          sub={
            stats
              ? t('alerts.confirmedInstant', {
                  confirmed: stats.confirmed_trades,
                  instant: stats.instant_trades,
                })
              : undefined
          }
          color="#3fb950"
        />
        <CompactStatCard
          compact
          label={t('alerts.avgConfirmTime')}
          value={stats ? `${stats.avg_confirm_minutes.toFixed(0)} min` : '—'}
          sub={stats ? t('alerts.pendingNow', { count: stats.pending_confirmations }) : undefined}
          color="#388bfd"
        />
        <CompactStatCard
          compact
          label={t('alerts.confirmFailed')}
          value={stats ? `${stats.confirm_failed_rate.toFixed(1)}%` : '—'}
          sub={stats ? t('alerts.signalsFailed', { count: stats.confirm_failed_count }) : undefined}
          color="#f85149"
        />
      </div>

      {/* Section 4: Trade history */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-[#e6edf3]">{t('alerts.tradeHistory')}</h2>
          <span className="rounded-full bg-[#388bfd]/20 px-2 py-0.5 font-mono text-[10px] font-bold text-[#388bfd]">
            {items.length}
          </span>
        </div>

        <TradeFilterBar
          statusFilter={statusFilter}
          strategyFilter={strategyFilter}
          tierFilter={tierFilter}
          directionFilter={directionFilter}
          timeRange={timeRange}
          symbolSearch={symbolSearch}
          statusCounts={statusCounts}
          onStatusChange={setStatusFilter}
          onStrategyChange={setStrategyFilter}
          onTierChange={setTierFilter}
          onDirectionChange={setDirectionFilter}
          onTimeRangeChange={setTimeRange}
          onSymbolSearchChange={setSymbolSearch}
        />

        <TradesTable items={items} opportunityMap={opportunityMap} loading={loading} />
      </div>
    </div>
  )
}
