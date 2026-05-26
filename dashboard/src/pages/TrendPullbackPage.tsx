import { TrendingUp } from 'lucide-react'
import { ClickableRow, ScannerPageLayout } from '../components/scanner/ScannerPageLayout'
import { useStrategyOpportunities } from '../hooks/useStrategyOpportunities'
import { useTranslation } from '../i18n/I18nProvider'
import { directionColor, scoreCircleColor } from '../utils/colors'
import { formatPct, formatPrice, pairLabel } from '../utils/format'

export function TrendPullbackPage() {
  const { t } = useTranslation()
  const { items, loading, error, refresh } = useStrategyOpportunities('TREND_PULLBACK')

  return (
    <ScannerPageLayout title={t('scanner.trendPullback')} description="Pullback entry within established H1 trend (EMA 20/50). Requires M15 confirmation. / Vào lệnh theo pullback trong xu hướng H1 (EMA 20/50). Cần xác nhận M15." icon={<TrendingUp className="h-5 w-5 text-[#3fb950]" />}
      loading={loading} error={error} onRefresh={refresh} items={items}
      header={
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
          <p className="text-[10px] text-[#8b949e]">Pullback Opportunities</p>
          <p className="font-mono text-2xl font-bold">{items.length}</p>
        </div>
      }>
      <div className="overflow-x-auto rounded-xl border border-[#30363d] bg-[#161b22]">
        <table className="w-full min-w-[700px] text-sm">
          <thead><tr className="border-b border-[#30363d] text-[10px] uppercase text-[#8b949e]">
            <th className="px-3 py-2 text-left">Symbol</th><th className="px-3 py-2 text-left">Trend</th><th className="px-3 py-2 text-left">Pullback %</th>
            <th className="px-3 py-2 text-left">EMA Dist</th><th className="px-3 py-2 text-left">Bounce</th><th className="px-3 py-2 text-left">Score</th>
          </tr></thead>
          <tbody>
            {items.map((item) => (
              <ClickableRow key={item.id} opp={item}>
                <td className="px-3 py-2 font-mono font-semibold">{pairLabel(item.symbol)}</td>
                <td className="px-3 py-2 font-mono text-xs" style={{ color: directionColor(item.direction) }}>{item.direction === 'LONG' ? 'UP' : 'DOWN'}</td>
                <td className="px-3 py-2 font-mono text-xs">{formatPct(String(item.context?.pullback_pct ?? ''))}</td>
                <td className="px-3 py-2 font-mono text-[10px] text-[#8b949e]">EMA20 {formatPrice(String(item.context?.ema20 ?? ''))}</td>
                <td className="px-3 py-2">{item.context?.bounce_confirmed ? '✅' : '—'}</td>
                <td className="px-3 py-2 font-mono font-bold" style={{ color: scoreCircleColor(item.total_score) }}>{item.total_score}</td>
              </ClickableRow>
            ))}
          </tbody>
        </table>
      </div>
    </ScannerPageLayout>
  )
}
