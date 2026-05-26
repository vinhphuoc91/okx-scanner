import { Radio } from 'lucide-react'
import { ClickableRow, ScannerPageLayout } from '../components/scanner/ScannerPageLayout'
import { useStrategyOpportunities } from '../hooks/useStrategyOpportunities'
import { useTranslation } from '../i18n/I18nProvider'
import { directionColor, scoreCircleColor } from '../utils/colors'
import { formatDateTimeShort, formatNumber, formatPct, formatPrice, pairLabel } from '../utils/format'

export function BreakoutScannerPage() {
  const { t } = useTranslation()
  const { items, loading, error, refresh } = useStrategyOpportunities('BREAKOUT')
  const avgBreakout = items.length
    ? items.reduce((s, i) => s + parseFloat(String(i.context?.breakout_pct ?? 0)), 0) / items.length
    : 0

  return (
    <ScannerPageLayout title={t('scanner.breakout')} description="Price breaking out of H1 consolidation range with 2× volume. Requires M15 confirmation. / Giá phá vỡ vùng tích lũy H1 kèm volume gấp 2×. Cần xác nhận M15." icon={<Radio className="h-5 w-5 text-[#d29922]" />}
      loading={loading} error={error} onRefresh={refresh} items={items}
      header={
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4"><p className="text-[10px] text-[#8b949e]">Breakouts</p><p className="font-mono text-2xl font-bold">{items.length}</p></div>
          <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4"><p className="text-[10px] text-[#8b949e]">Avg Breakout %</p><p className="font-mono text-2xl font-bold">{avgBreakout.toFixed(2)}%</p></div>
        </div>
      }>
      <div className="overflow-x-auto rounded-xl border border-[#30363d] bg-[#161b22]">
        <table className="w-full min-w-[800px] text-sm">
          <thead><tr className="border-b border-[#30363d] text-[10px] uppercase text-[#8b949e]">
            <th className="px-3 py-2 text-left">Symbol</th><th className="px-3 py-2 text-left">Dir</th><th className="px-3 py-2 text-left">Breakout %</th>
            <th className="px-3 py-2 text-left">Vol Ratio</th><th className="px-3 py-2 text-left">R / S</th><th className="px-3 py-2 text-left">Score</th><th className="px-3 py-2 text-left">Badge</th><th className="px-3 py-2 text-left">Detected</th>
          </tr></thead>
          <tbody>
            {items.map((item) => {
              const volRatio = parseFloat(String(item.context?.volume_ratio ?? 0))
              const confirmed = volRatio >= 2
              return (
                <ClickableRow key={item.id} opp={item}>
                  <td className="px-3 py-2 font-mono font-semibold">{pairLabel(item.symbol)}</td>
                  <td className="px-3 py-2 font-mono text-xs" style={{ color: directionColor(item.direction) }}>{item.direction}</td>
                  <td className="px-3 py-2 font-mono text-xs">{formatPct(String(item.context?.breakout_pct ?? ''))}</td>
                  <td className="px-3 py-2 font-mono text-xs">{formatNumber(volRatio, 1)}x</td>
                  <td className="px-3 py-2 font-mono text-[10px] text-[#8b949e]">
                    {formatPrice(String(item.context?.resistance ?? ''))} / {formatPrice(String(item.context?.support ?? ''))}
                  </td>
                  <td className="px-3 py-2 font-mono font-bold" style={{ color: scoreCircleColor(item.total_score) }}>{item.total_score}</td>
                  <td className="px-3 py-2"><span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${confirmed ? 'bg-[#3fb950]/20 text-[#3fb950]' : 'bg-[#d29922]/20 text-[#d29922]'}`}>{confirmed ? 'CONFIRMED' : 'WEAK'}</span></td>
                  <td className="px-3 py-2 font-mono text-[10px] text-[#8b949e]">{formatDateTimeShort(item.detected_at)}</td>
                </ClickableRow>
              )
            })}
          </tbody>
        </table>
      </div>
    </ScannerPageLayout>
  )
}
