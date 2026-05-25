import { Search, SlidersHorizontal } from 'lucide-react'
import { useState } from 'react'
import { TimeRangeFilter } from './TimeRangeFilter'
import { useTranslation } from '../../i18n/I18nProvider'
import type { StatusFilterKey } from '../../hooks/useAlerts'
import type { TimeRangeValue } from '../../utils/timeRange'
import type { StrategyFilterKey, TierFilterKey } from './PerformancePanels'

type DirectionFilter = 'all' | 'LONG' | 'SHORT'

const STATUS_TABS: { value: StatusFilterKey; labelKey: string }[] = [
  { value: 'all', labelKey: 'alerts.status.all' },
  { value: 'RUNNING', labelKey: 'alerts.status.running' },
  { value: 'WIN', labelKey: 'alerts.status.win' },
  { value: 'LOSS', labelKey: 'alerts.status.loss' },
  { value: 'EXPIRED', labelKey: 'alerts.status.expired' },
  { value: 'PENDING', labelKey: 'alerts.status.pending' },
  { value: 'CONFIRM_FAILED', labelKey: 'alerts.status.confirmFailed' },
]

const STRATEGY_OPTIONS: { value: StrategyFilterKey; labelKey: string }[] = [
  { value: 'all', labelKey: 'alerts.allStrategies' },
  { value: 'FUNDING', labelKey: 'strategy.fundingShort' },
  { value: 'MOMENTUM', labelKey: 'strategy.momentumShort' },
  { value: 'BREAKOUT', labelKey: 'strategy.breakoutShort' },
  { value: 'VOLUME_ANOMALY', labelKey: 'strategy.volumeAnomalyShort' },
  { value: 'TREND_PULLBACK', labelKey: 'strategy.trendPullbackShort' },
  { value: 'CORRELATION_DIVERGENCE', labelKey: 'strategy.correlationDivergenceShort' },
  { value: 'LIQUIDATION_ZONE', labelKey: 'strategy.liquidationZoneShort' },
  { value: 'STAT_ARBITRAGE', labelKey: 'strategy.statArbitrageShort' },
]

interface TradeFilterBarProps {
  statusFilter: StatusFilterKey
  strategyFilter: StrategyFilterKey
  tierFilter: TierFilterKey
  directionFilter: DirectionFilter
  timeRange: TimeRangeValue
  symbolSearch: string
  statusCounts: Record<StatusFilterKey, number>
  onStatusChange: (v: StatusFilterKey) => void
  onStrategyChange: (v: StrategyFilterKey) => void
  onTierChange: (v: TierFilterKey) => void
  onDirectionChange: (v: DirectionFilter) => void
  onTimeRangeChange: (v: TimeRangeValue) => void
  onSymbolSearchChange: (v: string) => void
}

export function TradeFilterBar({
  statusFilter,
  strategyFilter,
  tierFilter,
  directionFilter,
  timeRange,
  symbolSearch,
  statusCounts,
  onStatusChange,
  onStrategyChange,
  onTierChange,
  onDirectionChange,
  onTimeRangeChange,
  onSymbolSearchChange,
}: TradeFilterBarProps) {
  const { t } = useTranslation()
  const [mobileOpen, setMobileOpen] = useState(false)

  const selectClass =
    'rounded-md border border-[#30363d] bg-[#21262d] px-2.5 py-1.5 text-xs text-[#e6edf3]'

  const dropdowns = (
    <>
      <select
        value={strategyFilter}
        onChange={(e) => onStrategyChange(e.target.value as StrategyFilterKey)}
        className={selectClass}
      >
        {STRATEGY_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {t(o.labelKey)}
          </option>
        ))}
      </select>
      <select
        value={tierFilter}
        onChange={(e) => onTierChange(e.target.value as TierFilterKey)}
        className={selectClass}
      >
        <option value="all">{t('alerts.allTiers')}</option>
        <option value="1">{t('alerts.tier1')}</option>
        <option value="2">{t('alerts.tier2')}</option>
        <option value="3">{t('alerts.tier3')}</option>
      </select>
      <select
        value={directionFilter}
        onChange={(e) => onDirectionChange(e.target.value as DirectionFilter)}
        className={selectClass}
      >
        <option value="all">{t('alerts.allDirections')}</option>
        <option value="LONG">{t('alerts.long')}</option>
        <option value="SHORT">{t('alerts.short')}</option>
      </select>
      <TimeRangeFilter value={timeRange} onChange={onTimeRangeChange} />
    </>
  )

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {STATUS_TABS.map((tab) => {
          const count = statusCounts[tab.value]
          const active = statusFilter === tab.value
          return (
            <button
              key={tab.value}
              type="button"
              onClick={() => onStatusChange(tab.value)}
              className={`rounded-md px-2.5 py-1 text-[11px] font-medium whitespace-nowrap ${
                active
                  ? 'bg-[#388bfd] text-white'
                  : 'border border-[#30363d] text-[#8b949e] hover:text-[#e6edf3]'
              }`}
            >
              {t(tab.labelKey)}
              {count > 0 && (
                <span className={`ml-1 font-mono ${active ? 'text-white/80' : 'text-[#484f58]'}`}>
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[140px] flex-1 sm:max-w-[200px]">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#484f58]" />
          <input
            type="search"
            value={symbolSearch}
            onChange={(e) => onSymbolSearchChange(e.target.value)}
            placeholder={t('alerts.searchSymbol')}
            className="w-full rounded-md border border-[#30363d] bg-[#21262d] py-1.5 pl-8 pr-2 text-xs text-[#e6edf3] placeholder:text-[#484f58]"
          />
        </div>

        <button
          type="button"
          onClick={() => setMobileOpen((o) => !o)}
          className="flex items-center gap-1 rounded-md border border-[#30363d] px-2.5 py-1.5 text-xs text-[#8b949e] hover:text-[#e6edf3] lg:hidden"
        >
          <SlidersHorizontal className="h-3.5 w-3.5" />
          {t('alerts.filters')}
        </button>

        <div
          className={`${mobileOpen ? 'flex' : 'hidden'} w-full flex-wrap items-center gap-2 lg:flex lg:w-auto`}
        >
          {dropdowns}
        </div>
      </div>
    </div>
  )
}
