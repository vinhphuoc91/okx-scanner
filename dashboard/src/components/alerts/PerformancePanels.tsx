import { useTranslation } from '../../i18n/I18nProvider'
import type { AlertStatsResponse, StrategyStats } from '../../types/api'
import { tierColor } from '../../utils/colors'
import { formatPctColored } from '../../utils/format'

export type StrategyFilterKey =
  | 'all'
  | 'FUNDING'
  | 'MOMENTUM'
  | 'BREAKOUT'
  | 'VOLUME_ANOMALY'
  | 'TREND_PULLBACK'
  | 'CORRELATION_DIVERGENCE'
  | 'LIQUIDATION_ZONE'
  | 'STAT_ARBITRAGE'

export type TierFilterKey = 'all' | '1' | '2' | '3'

const STRATEGY_ROWS: {
  key: StrategyFilterKey
  shortKey: string
  icon: string
  color: string
}[] = [
  { key: 'FUNDING', shortKey: 'strategy.fundingShort', icon: '💰', color: '#f85149' },
  { key: 'MOMENTUM', shortKey: 'strategy.momentumShort', icon: '📈', color: '#388bfd' },
  { key: 'BREAKOUT', shortKey: 'strategy.breakoutShort', icon: '🚀', color: '#a371f7' },
  { key: 'VOLUME_ANOMALY', shortKey: 'strategy.volumeAnomalyShort', icon: '📊', color: '#d29922' },
  { key: 'TREND_PULLBACK', shortKey: 'strategy.trendPullbackShort', icon: '📉', color: '#3fb950' },
  { key: 'CORRELATION_DIVERGENCE', shortKey: 'strategy.correlationDivergenceShort', icon: '🔀', color: '#79c0ff' },
  { key: 'LIQUIDATION_ZONE', shortKey: 'strategy.liquidationZoneShort', icon: '💥', color: '#ff7b72' },
  { key: 'STAT_ARBITRAGE', shortKey: 'strategy.statArbitrageShort', icon: '⚖️', color: '#e3b341' },
]

function StatCell({ value, color }: { value: string; color?: string }) {
  return (
    <span className="font-mono text-[11px] font-semibold tabular-nums" style={{ color: color ?? '#e6edf3' }}>
      {value}
    </span>
  )
}

function StrategyRow({
  icon,
  label,
  stats,
  color,
  active,
  onClick,
}: {
  icon: string
  label: string
  stats: StrategyStats | undefined
  color: string
  active: boolean
  onClick: () => void
}) {
  const pnl = stats ? formatPctColored(stats.avg_pnl) : null

  return (
    <button
      type="button"
      onClick={onClick}
      className={`grid w-full grid-cols-[1fr_auto_auto_auto] items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-[#21262d] ${
        active ? 'bg-[#388bfd]/10 ring-1 ring-[#388bfd]/40' : ''
      }`}
    >
      <span className="flex min-w-0 items-center gap-1.5 truncate text-xs font-medium" style={{ color }}>
        <span>{icon}</span>
        <span className="truncate">{label}</span>
      </span>
      <StatCell value={String(stats?.count ?? 0)} />
      <StatCell value={stats ? `${stats.win_rate.toFixed(0)}%` : '—'} />
      <StatCell value={pnl?.text ?? '—'} color={pnl?.color} />
    </button>
  )
}

function TierRow({
  tier,
  stats,
  active,
  onClick,
}: {
  tier: number
  stats: StrategyStats | undefined
  active: boolean
  onClick: () => void
}) {
  const { t } = useTranslation()
  const color = tierColor(tier)
  const tierLabel =
    tier === 1 ? t('alerts.tier1Short') : tier === 2 ? t('alerts.tier2Short') : t('alerts.tier3Short')
  const pnl = stats ? formatPctColored(stats.avg_pnl) : null

  return (
    <button
      type="button"
      onClick={onClick}
      className={`grid w-full grid-cols-[1fr_auto_auto_auto] items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-[#21262d] ${
        active ? 'bg-[#388bfd]/10 ring-1 ring-[#388bfd]/40' : ''
      }`}
    >
      <span
        className="inline-flex w-fit rounded px-1.5 py-0.5 text-[10px] font-bold"
        style={{ color, backgroundColor: `${color}22` }}
      >
        {tierLabel}
      </span>
      <StatCell value={String(stats?.count ?? 0)} />
      <StatCell value={stats ? `${stats.win_rate.toFixed(0)}%` : '—'} />
      <StatCell value={pnl?.text ?? '—'} color={pnl?.color} />
    </button>
  )
}

interface PerformancePanelsProps {
  stats: AlertStatsResponse | null
  strategyFilter: StrategyFilterKey
  tierFilter: TierFilterKey
  onStrategyFilter: (key: StrategyFilterKey) => void
  onTierFilter: (key: TierFilterKey) => void
}

export function PerformancePanels({
  stats,
  strategyFilter,
  tierFilter,
  onStrategyFilter,
  onTierFilter,
}: PerformancePanelsProps) {
  const { t } = useTranslation()

  const toggleStrategy = (key: StrategyFilterKey) => {
    onStrategyFilter(strategyFilter === key ? 'all' : key)
  }

  const toggleTier = (key: TierFilterKey) => {
    onTierFilter(tierFilter === key ? 'all' : key)
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-3">
        <div className="mb-2 flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-[#8b949e]">
          <span>{t('alerts.perfByStrategy')}</span>
          <span className="grid grid-cols-3 gap-2 text-right normal-case">
            <span>{t('alerts.metric.trades')}</span>
            <span>{t('alerts.metric.winRate')}</span>
            <span>{t('alerts.metric.avgPnl')}</span>
          </span>
        </div>
        <div className="space-y-0.5">
          {STRATEGY_ROWS.map((row) => (
            <StrategyRow
              key={row.key}
              icon={row.icon}
              label={t(row.shortKey)}
              stats={stats?.by_strategy[row.key]}
              color={row.color}
              active={strategyFilter === row.key}
              onClick={() => toggleStrategy(row.key)}
            />
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-3">
        <div className="mb-2 flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-[#8b949e]">
          <span>{t('alerts.perfByTier')}</span>
          <span className="grid grid-cols-3 gap-2 text-right normal-case">
            <span>{t('alerts.metric.count')}</span>
            <span>{t('alerts.metric.winRate')}</span>
            <span>{t('alerts.metric.avgPnl')}</span>
          </span>
        </div>
        <div className="space-y-0.5">
          {[1, 2, 3].map((tier) => (
            <TierRow
              key={tier}
              tier={tier}
              stats={stats?.by_tier[String(tier)]}
              active={tierFilter === String(tier)}
              onClick={() => toggleTier(String(tier) as TierFilterKey)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
