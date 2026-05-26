import { Flame } from 'lucide-react'
import { useMemo, useState } from 'react'
import { ClickableRow, ScannerPageLayout } from '../components/scanner/ScannerPageLayout'
import { useStrategyOpportunities } from '../hooks/useStrategyOpportunities'
import { useTranslation } from '../i18n/I18nProvider'
import { directionColor, scoreCircleColor } from '../utils/colors'
import {
  contextFunding,
  contextPrice,
  contextSpread,
  contextVolume,
  formatFunding,
  pairLabel,
} from '../utils/format'

export function FundingScannerPage() {
  const { t } = useTranslation()
  const { items, loading, error, refresh } = useStrategyOpportunities('FUNDING')
  const [dirFilter, setDirFilter] = useState<'all' | 'LONG' | 'SHORT'>('all')

  const filtered = useMemo(
    () => items.filter((i) => dirFilter === 'all' || i.direction === dirFilter),
    [items, dirFilter],
  )

  const rates = items.map((i) => parseFloat(String(i.context?.funding_rate ?? 0)))
  const avgRate = rates.length ? rates.reduce((a, b) => a + b, 0) / rates.length : 0
  const extremePos = rates.filter((r) => r > 0.0005).length
  const extremeNeg = rates.filter((r) => r < -0.0002).length

  const heatmap = [...items]
    .sort((a, b) => Math.abs(parseFloat(String(b.context?.funding_rate ?? 0))) - Math.abs(parseFloat(String(a.context?.funding_rate ?? 0))))
    .slice(0, 20)

  const heatColor = (rate: number) => {
    if (rate > 0.0005) return '#f85149'
    if (rate > 0) return '#d29922'
    if (rate < -0.0002) return '#3fb950'
    return '#484f58'
  }

  return (
    <ScannerPageLayout
      title={t('scanner.funding')}
      description="Detects extreme funding rates → extreme positive = SHORT, extreme negative = LONG. No M15 confirmation. / Phát hiện funding rate bất thường. Funding dương cao → SHORT; âm cao → LONG. Không cần xác nhận M15."
      icon={<Flame className="h-5 w-5 text-[#f85149]" />}
      loading={loading}
      error={error}
      onRefresh={refresh}
      items={filtered}
      emptyTitle="No funding opportunities"
      header={
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            { label: 'Total Signals', value: String(items.length) },
            { label: 'Avg Funding Rate', value: formatFunding(avgRate) },
            { label: 'Extreme Positive', value: String(extremePos), color: '#f85149' },
            { label: 'Extreme Negative', value: String(extremeNeg), color: '#3fb950' },
          ].map((c) => (
            <div key={c.label} className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
              <p className="text-[10px] uppercase text-[#8b949e]">{c.label}</p>
              <p className="font-mono text-xl font-bold" style={{ color: c.color ?? '#e6edf3' }}>{c.value}</p>
            </div>
          ))}
        </div>
      }
      filters={
        <div className="flex gap-2">
          {(['all', 'LONG', 'SHORT'] as const).map((f) => (
            <button key={f} type="button" onClick={() => setDirFilter(f)}
              className={`rounded-md px-3 py-1.5 text-xs ${dirFilter === f ? 'bg-[#388bfd] text-white' : 'border border-[#30363d] text-[#8b949e]'}`}>
              {f === 'all' ? 'All' : f}
            </button>
          ))}
        </div>
      }
    >
      {heatmap.length > 0 && (
        <div className="mb-4 rounded-xl border border-[#30363d] bg-[#161b22] p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase text-[#8b949e]">Funding Heatmap</h3>
          <div className="grid grid-cols-4 gap-1.5 sm:grid-cols-5 md:grid-cols-10">
            {heatmap.map((item) => {
              const rate = parseFloat(String(item.context?.funding_rate ?? 0))
              return (
                <div key={item.id} data-opp-id={item.id}
                  className="cursor-pointer rounded p-2 text-center transition-transform hover:scale-105"
                  style={{ backgroundColor: heatColor(rate) + '33', border: `1px solid ${heatColor(rate)}55` }}>
                  <p className="truncate text-[9px] font-mono">{pairLabel(item.symbol).split('/')[0]}</p>
                  <p className="font-mono text-[10px] font-bold" style={{ color: heatColor(rate) }}>
                    {formatFunding(rate)}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      )}
      <div className="overflow-x-auto rounded-xl border border-[#30363d] bg-[#161b22]">
        <table className="w-full min-w-[800px] text-sm">
          <thead>
            <tr className="border-b border-[#30363d] text-[10px] uppercase text-[#8b949e]">
              <th className="px-3 py-2 text-left">Symbol</th>
              <th className="px-3 py-2 text-left">Price</th>
              <th className="px-3 py-2 text-left">Funding</th>
              <th className="px-3 py-2 text-left">Direction</th>
              <th className="px-3 py-2 text-left">Score</th>
              <th className="px-3 py-2 text-left">Volume</th>
              <th className="px-3 py-2 text-left">Spread</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <ClickableRow key={item.id} opp={item}>
                <td className="px-3 py-2 font-mono font-semibold">{pairLabel(item.symbol)}</td>
                <td className="px-3 py-2 font-mono text-xs text-[#e6edf3]">{contextPrice(item.context)}</td>
                <td className="px-3 py-2 font-mono text-xs">{contextFunding(item.context)}</td>
                <td className="px-3 py-2 font-mono text-xs" style={{ color: directionColor(item.direction) }}>{item.direction}</td>
                <td className="px-3 py-2 font-mono font-bold" style={{ color: scoreCircleColor(item.total_score) }}>{item.total_score}</td>
                <td className="px-3 py-2 font-mono text-xs text-[#8b949e]">{contextVolume(item.context)}</td>
                <td className="px-3 py-2 font-mono text-xs text-[#8b949e]">{contextSpread(item.context)}</td>
              </ClickableRow>
            ))}
          </tbody>
        </table>
      </div>
    </ScannerPageLayout>
  )
}
