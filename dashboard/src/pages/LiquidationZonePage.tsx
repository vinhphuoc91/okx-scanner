import { AlertTriangle } from 'lucide-react'
import { useMemo } from 'react'
import { ClickableRow, ScannerPageLayout } from '../components/scanner/ScannerPageLayout'
import { useStrategyOpportunities } from '../hooks/useStrategyOpportunities'
import { useTranslation } from '../i18n/I18nProvider'
import { directionColor, scoreCircleColor } from '../utils/colors'
import { contextFunding, formatNumber, pairLabel } from '../utils/format'

function ctxNum(value: unknown): number | undefined {
  const n = parseFloat(String(value ?? ''))
  return Number.isNaN(n) ? undefined : n
}

export function LiquidationZonePage() {
  const { t } = useTranslation()
  const { items, loading, error, refresh } = useStrategyOpportunities('LIQUIDATION_ZONE')

  const avgOi = useMemo(() => {
    const vals = items.map((i) => parseFloat(String(i.context?.oi_change_4h ?? 0)))
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0
  }, [items])

  const extremeFunding = items.filter((i) => {
    const r = parseFloat(String(i.context?.funding_rate ?? 0))
    return r >= 0.0005 || r <= -0.0002
  }).length

  return (
    <ScannerPageLayout
      title={t('scanner.liquidationZone')}
      description="Fades over-leveraged markets: extreme funding + OI change ≥8% in 4H + RSI exhaustion. Requires M15 confirmation. / Vào ngược thị trường quá đòn bẩy: funding extreme + OI thay đổi ≥8%/4H + RSI kiệt sức. Cần xác nhận M15."
      icon={<AlertTriangle className="h-5 w-5 text-[#f85149]" />}
      loading={loading}
      error={error}
      onRefresh={refresh}
      items={items}
      emptyTitle={t('scanner.liquidationEmpty')}
      header={
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
          {[
            { label: t('scanner.liqOverLeveraged'), value: String(items.length) },
            { label: t('scanner.liqAvgOi'), value: `${formatNumber(avgOi, 1)}%` },
            { label: t('scanner.liqExtremeFunding'), value: String(extremeFunding), color: '#f85149' },
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
        <table className="w-full min-w-[900px] text-sm">
          <thead>
            <tr className="border-b border-[#30363d] text-[10px] uppercase text-[#8b949e]">
              <th className="px-3 py-2 text-left">Symbol</th>
              <th className="px-3 py-2 text-left">OI Change 4H</th>
              <th className="px-3 py-2 text-left">Funding</th>
              <th className="px-3 py-2 text-left">RSI</th>
              <th className="px-3 py-2 text-left">BB Position</th>
              <th className="px-3 py-2 text-left">Direction</th>
              <th className="px-3 py-2 text-left">Score</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <ClickableRow key={item.id} opp={item}>
                <td className="px-3 py-2 font-mono font-semibold">{pairLabel(item.symbol)}</td>
                <td className="px-3 py-2 font-mono text-xs">{formatNumber(ctxNum(item.context?.oi_change_4h), 1)}%</td>
                <td className="px-3 py-2 font-mono text-xs">{contextFunding(item.context)}</td>
                <td className="px-3 py-2 font-mono text-xs">{formatNumber(ctxNum(item.context?.rsi), 1)}</td>
                <td className="px-3 py-2 font-mono text-xs">{formatNumber(ctxNum(item.context?.bb_position), 2)}</td>
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
