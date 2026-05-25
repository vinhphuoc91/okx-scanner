import { Activity } from 'lucide-react'
import { ClickableRow, ScannerPageLayout } from '../components/scanner/ScannerPageLayout'
import { useStrategyOpportunities } from '../hooks/useStrategyOpportunities'
import { useTranslation } from '../i18n/I18nProvider'
import { directionColor, scoreCircleColor } from '../utils/colors'
import { formatDateTimeShort, formatPct, pairLabel } from '../utils/format'

export function VolumeAnomalyPage() {
  const { t } = useTranslation()
  const { items, loading, error, refresh } = useStrategyOpportunities('VOLUME_ANOMALY')
  const avgRatio = items.length
    ? items.reduce((s, i) => s + parseFloat(String(i.context?.volume_ratio ?? 0)), 0) / items.length
    : 0

  return (
    <ScannerPageLayout title={t('scanner.volumeAnomaly')} icon={<Activity className="h-5 w-5 text-[#388bfd]" />}
      loading={loading} error={error} onRefresh={refresh} items={items}
      header={
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4"><p className="text-[10px] text-[#8b949e]">Spikes Detected</p><p className="font-mono text-2xl font-bold">{items.length}</p></div>
          <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4"><p className="text-[10px] text-[#8b949e]">Avg Volume Ratio</p><p className="font-mono text-2xl font-bold">{avgRatio.toFixed(1)}x</p></div>
        </div>
      }>
      <div className="overflow-x-auto rounded-xl border border-[#30363d] bg-[#161b22]">
        <table className="w-full min-w-[700px] text-sm">
          <thead><tr className="border-b border-[#30363d] text-[10px] uppercase text-[#8b949e]">
            <th className="px-3 py-2 text-left">Symbol</th><th className="px-3 py-2 text-left">Vol Ratio</th><th className="px-3 py-2 text-left">Bar</th>
            <th className="px-3 py-2 text-left">Price Δ%</th><th className="px-3 py-2 text-left">Dir</th><th className="px-3 py-2 text-left">Score</th><th className="px-3 py-2 text-left">Time</th>
          </tr></thead>
          <tbody>
            {items.map((item) => {
              const ratio = parseFloat(String(item.context?.volume_ratio ?? 0))
              const barPct = Math.min(100, (ratio / 8) * 100)
              return (
                <ClickableRow key={item.id} opp={item}>
                  <td className="px-3 py-2 font-mono font-semibold">{pairLabel(item.symbol)}</td>
                  <td className="px-3 py-2 font-mono text-xs">{ratio.toFixed(1)}x</td>
                  <td className="px-3 py-2"><div className="h-2 w-24 overflow-hidden rounded-full bg-[#21262d]"><div className="h-full rounded-full bg-[#388bfd]" style={{ width: `${barPct}%` }} /></div></td>
                  <td className="px-3 py-2 font-mono text-xs">{formatPct(String(item.context?.price_change_pct ?? ''))}</td>
                  <td className="px-3 py-2 font-mono text-xs" style={{ color: directionColor(item.direction) }}>{item.direction}</td>
                  <td className="px-3 py-2 font-mono font-bold" style={{ color: scoreCircleColor(item.total_score) }}>{item.total_score}</td>
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
