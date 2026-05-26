import { GitCompare } from 'lucide-react'
import { useMemo } from 'react'
import { ClickableRow, ScannerPageLayout } from '../components/scanner/ScannerPageLayout'
import { useStrategyOpportunities } from '../hooks/useStrategyOpportunities'
import { useTranslation } from '../i18n/I18nProvider'
import { directionColor, scoreCircleColor } from '../utils/colors'
import { formatNumber, pairLabel } from '../utils/format'

function ctxNum(value: unknown): number | undefined {
  const n = parseFloat(String(value ?? ''))
  return Number.isNaN(n) ? undefined : n
}

export function CorrelationDivergencePage() {
  const { t } = useTranslation()
  const { items, loading, error, refresh } = useStrategyOpportunities('CORRELATION_DIVERGENCE')

  const avgDiv = useMemo(() => {
    const vals = items.map((i) => parseFloat(String(i.context?.divergence_pct ?? 0)))
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0
  }, [items])

  const btcChange = ctxNum(items[0]?.context?.btc_change_1h)
  const ethChange = ctxNum(items[0]?.context?.eth_change_1h)

  return (
    <ScannerPageLayout
      title={t('scanner.correlationDivergence')}
      description="Coins diverging from BTC/ETH benchmark — expects catch-up move. Tier 2+ only. / Coin phân kỳ so với BTC/ETH — kỳ vọng bắt kịp. Chỉ scan Tier 2+."
      icon={<GitCompare className="h-5 w-5 text-[#79c0ff]" />}
      loading={loading}
      error={error}
      onRefresh={refresh}
      items={items}
      emptyTitle={t('scanner.correlationEmpty')}
      header={
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            { label: t('scanner.corrSignals'), value: String(items.length) },
            { label: t('scanner.corrAvgDiv'), value: `${formatNumber(avgDiv, 2)}%` },
            { label: t('scanner.corrBtc1h'), value: btcChange != null ? `${formatNumber(btcChange, 2)}%` : '—' },
            { label: t('scanner.corrEth1h'), value: ethChange != null ? `${formatNumber(ethChange, 2)}%` : '—' },
          ].map((c) => (
            <div key={c.label} className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
              <p className="text-[10px] uppercase text-[#8b949e]">{c.label}</p>
              <p className="font-mono text-xl font-bold text-[#e6edf3]">{c.value}</p>
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
              <th className="px-3 py-2 text-left">BTC Δ1H</th>
              <th className="px-3 py-2 text-left">Coin Δ1H</th>
              <th className="px-3 py-2 text-left">Divergence</th>
              <th className="px-3 py-2 text-left">Direction</th>
              <th className="px-3 py-2 text-left">Score</th>
              <th className="px-3 py-2 text-left">Tier</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <ClickableRow key={item.id} opp={item}>
                <td className="px-3 py-2 font-mono font-semibold">{pairLabel(item.symbol)}</td>
                <td className="px-3 py-2 font-mono text-xs">{formatNumber(ctxNum(item.context?.btc_change_1h), 2)}%</td>
                <td className="px-3 py-2 font-mono text-xs">{formatNumber(ctxNum(item.context?.coin_change_1h), 2)}%</td>
                <td className="px-3 py-2 font-mono text-xs text-[#79c0ff]">{formatNumber(ctxNum(item.context?.divergence_pct), 2)}%</td>
                <td className="px-3 py-2 font-mono text-xs" style={{ color: directionColor(item.direction) }}>{item.direction}</td>
                <td className="px-3 py-2 font-mono font-bold" style={{ color: scoreCircleColor(item.total_score) }}>{item.total_score}</td>
                <td className="px-3 py-2 font-mono text-xs text-[#8b949e]">{item.tier ?? '—'}</td>
              </ClickableRow>
            ))}
          </tbody>
        </table>
      </div>
    </ScannerPageLayout>
  )
}
