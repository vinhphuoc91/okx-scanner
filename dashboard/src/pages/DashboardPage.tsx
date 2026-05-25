import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import type { DashboardData } from '../hooks/useDashboardData'
import type { GradeFilter, StrategyFilter } from '../types/api'
import { filterOpportunities } from '../utils/colors'
import { useTranslation } from '../i18n/I18nProvider'
import { FilterTabs } from '../components/dashboard/FilterTabs'
import { FundingHeatmap } from '../components/dashboard/FundingHeatmap'
import { MarketStatCards } from '../components/dashboard/MarketStatCards'
import { OpportunitiesTable } from '../components/dashboard/OpportunitiesTable'
import { RecentAlerts } from '../components/dashboard/RecentAlerts'
import { ScannerStats } from '../components/dashboard/ScannerStats'
import { ScoreDistributionChart } from '../components/dashboard/ScoreDistributionChart'
import { SystemStatus } from '../components/dashboard/SystemStatus'

export function DashboardPage() {
  const { t } = useTranslation()
  const { opportunities, stats, status, health, loading } =
    useOutletContext<DashboardData>()
  const [gradeFilter, setGradeFilter] = useState<GradeFilter>('all')
  const [strategyFilter, setStrategyFilter] = useState<StrategyFilter>('all')

  const filtered = filterOpportunities(opportunities, gradeFilter, strategyFilter)

  return (
    <div className="flex min-h-full flex-col">
      <div className="space-y-4 p-6">
        <MarketStatCards opportunities={opportunities} stats={stats} status={status} />

        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[#e6edf3]">{t('dashboard.topOpportunities')}</h2>
          </div>
          <FilterTabs
            gradeFilter={gradeFilter}
            strategyFilter={strategyFilter}
            onGradeChange={setGradeFilter}
            onStrategyChange={setStrategyFilter}
            count={filtered.length}
          />
          <div className="mt-3">
            <OpportunitiesTable items={filtered} loading={loading} />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <ScoreDistributionChart stats={stats} loading={loading} />
          <FundingHeatmap opportunities={opportunities} loading={loading} />
          <ScannerStats status={status} loading={loading} />
          <SystemStatus health={health} loading={loading} />
        </div>
      </div>

      <RecentAlerts opportunities={opportunities} />
    </div>
  )
}
