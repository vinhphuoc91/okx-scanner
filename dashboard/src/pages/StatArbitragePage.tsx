import { ArrowLeftRight } from 'lucide-react'
import { useMemo } from 'react'
import { ClickableRow, ScannerPageLayout } from '../components/scanner/ScannerPageLayout'
import { useStrategyOpportunities } from '../hooks/useStrategyOpportunities'
import { useTranslation } from '../i18n/I18nProvider'
import { directionColor, scoreCircleColor } from '../utils/colors'
import { contextFunding, contextPrice, formatNumber, pairLabel } from '../utils/format'

function ctxNum(value: unknown): number | undefined {
  const n = parseFloat(String(value ?? ''))
  return Number.isNaN(n) ? undefined : n
}

export function StatArbitragePage() {
  const { t } = useTranslation()
  const { items, loading, error, refresh } = useStrategyOpportunities('STAT_ARBITRAGE')

  const basisVals = useMemo(
    () => items.map((i) => parseFloat(String(i.context?.basis_pct ?? 0))),
    [items],
  )
  const avgBasis = basisVals.length ? basisVals.reduce((a, b) => a + b, 0) / basisVals.length : 0
  const highPremium = basisVals.filter((b) => b >= 0.3).length
  const lowPremium = basisVals.filter((b) => b <= -0.2).length

  return (
    <ScannerPageLayout
      title={t('scanner.statArbitrage')}
      description="Trades spot vs perp price gap (basis). Expects convergence when basis is too wide. / Giao dịch chênh lệch spot vs perp. Kỳ vọng hội tụ khi basis quá rộng."
      icon={<ArrowLeftRight className="h-5 w-5 text-[#e3b341]" />}
      loading={loading}
      error={error}
      onRefresh={refresh}
      items={items}
      emptyTitle={t('scanner.statArbEmpty')}
      header={
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            { label: t('scanner.statArbCount'), value: String(items.length) },
            { label: t('scanner.statArbAvgBasis'), value: `${formatNumber(avgBasis, 3)}%` },
            { label: t('scanner.statArbHigh'), value: String(highPremium), color: '#f85149' },
            { label: t('scanner.statArbLow'), value: String(lowPremium), color: '#3fb950' },
          ].map((c) => (
            <div key={c.label} className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
              <p className="text-[10px] uppercase text-[#8b949e]">{c.label}</p>
              <p className="font-mono text-xl font-bold" style={{ color: c.color ?? '#e6edf3' }}>{c.value}</p>
            </div>
          ))}
        </div>
      }
    >
      <div className="overflow-x-auto rounded-xl border border-[#30363d] bg-[#161b22]">
        <table className="w-full min-w-[1000px] text-sm">
          <thead>
            <tr className="border-b border-[#30363d] text-[10px] uppercase text-[#8b949e]">
              <th className="px-3 py-2 text-left">Symbol</th>
              <th className="px-3 py-2 text-left">Spot</th>
              <th className="px-3 py-2 text-left">Perp</th>
              <th className="px-3 py-2 text-left">Basis %</th>
              <th className="px-3 py-2 text-left">Basis Trend</th>
              <th className="px-3 py-2 text-left">Funding</th>
              <th className="px-3 py-2 text-left">Direction</th>
              <th className="px-3 py-2 text-left">Score</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <ClickableRow key={item.id} opp={item}>
                <td className="px-3 py-2 font-mono font-semibold">{pairLabel(item.symbol)}</td>
                <td className="px-3 py-2 font-mono text-xs">{contextPrice({ last_price: item.context?.spot_price })}</td>
                <td className="px-3 py-2 font-mono text-xs">{contextPrice({ last_price: item.context?.perp_price })}</td>
                <td className="px-3 py-2 font-mono text-xs text-[#e3b341]">{formatNumber(ctxNum(item.context?.basis_pct), 3)}%</td>
                <td className="px-3 py-2 font-mono text-xs">{formatNumber(ctxNum(item.context?.basis_trend), 3)}</td>
                <td className="px-3 py-2 font-mono text-xs">{contextFunding(item.context)}</td>
                <td className="px-3 py-2 font-mono text-xs" style={{ color: directionColor(item.direction) }}>{item.direction}</td>
                <td className="px-3 py-2 font-mono font-bold" style={{ color: scoreCircleColor(item.total_score) }}>{item.total_score}</td>
              </ClickableRow>
            ))}
          </tbody>
        </table>
      </div>
    </ScannerPageLayout>
  )
}
