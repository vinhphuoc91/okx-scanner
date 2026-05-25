import type { GradeFilter, StrategyFilter } from '../../types/api'
import { useTranslation } from '../../i18n/I18nProvider'

interface Props {
  gradeFilter: GradeFilter
  strategyFilter: StrategyFilter
  onGradeChange: (g: GradeFilter) => void
  onStrategyChange: (s: StrategyFilter) => void
  count: number
}

export function FilterTabs({
  gradeFilter,
  strategyFilter,
  onGradeChange,
  onStrategyChange,
  count,
}: Props) {
  const { t } = useTranslation()

  const TABS: { id: GradeFilter; labelKey: string; range: string }[] = [
    { id: 'all', labelKey: 'dashboard.grade.all', range: '' },
    { id: 'excellent', labelKey: 'dashboard.grade.excellent', range: '≥85' },
    { id: 'good', labelKey: 'dashboard.grade.good', range: '75–84' },
    { id: 'watch', labelKey: 'dashboard.grade.watch', range: '65–74' },
  ]

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap gap-1 rounded-lg border border-[#30363d] bg-[#0d1117] p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => onGradeChange(tab.id)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              gradeFilter === tab.id
                ? 'bg-[#388bfd] text-white'
                : 'text-[#8b949e] hover:text-[#e6edf3]'
            }`}
          >
            {t(tab.labelKey)}
            {tab.range && (
              <span className="ml-1 font-mono text-[10px] opacity-70">({tab.range})</span>
            )}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <select
          value={strategyFilter}
          onChange={(e) => onStrategyChange(e.target.value as StrategyFilter)}
          className="rounded-lg border border-[#30363d] bg-[#21262d] px-3 py-1.5 text-xs text-[#e6edf3] outline-none focus:border-[#388bfd]"
        >
          <option value="all">{t('dashboard.allStrategies')}</option>
          <option value="FUNDING">{t('strategy.fundingShort')}</option>
          <option value="MOMENTUM">{t('strategy.momentumShort')}</option>
        </select>
        <span className="text-xs text-[#8b949e]">
          <span className="font-mono font-semibold text-[#e6edf3]">{count}</span> {t('common.results')}
        </span>
      </div>
    </div>
  )
}
