import { Zap } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { ClickableRow, ScannerPageLayout } from '../components/scanner/ScannerPageLayout'
import { useStrategyOpportunities } from '../hooks/useStrategyOpportunities'
import { useTranslation } from '../i18n/I18nProvider'
import { directionColor, scoreCircleColor, tierColor } from '../utils/colors'
import { formatNumber, pairLabel } from '../utils/format'

export function MomentumScannerPage() {
  const { t } = useTranslation()
  const { items, loading, error, refresh } = useStrategyOpportunities('MOMENTUM')
  const [filter, setFilter] = useState<'all' | 'bullish' | 'bearish'>('all')
  const [tierF, setTierF] = useState<string>('all')

  const filtered = useMemo(() => {
    return items.filter((i) => {
      if (tierF !== 'all' && String(i.tier) !== tierF) return false
      if (filter === 'bullish' && i.direction !== 'LONG') return false
      if (filter === 'bearish' && i.direction !== 'SHORT') return false
      return true
    })
  }, [items, filter, tierF])

  const bullish = items.filter((i) => i.direction === 'LONG').length
  const bearish = items.filter((i) => i.direction === 'SHORT').length
  const donut = [
    { name: 'Bullish', value: bullish, color: '#3fb950' },
    { name: 'Bearish', value: bearish, color: '#f85149' },
  ].filter((d) => d.value > 0)

  return (
    <ScannerPageLayout
      title={t('scanner.momentum')}
      icon={<Zap className="h-5 w-5 text-[#388bfd]" />}
      loading={loading}
      error={error}
      onRefresh={refresh}
      items={filtered}
      header={
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4 md:col-span-3">
            <div className="grid grid-cols-3 gap-4">
              <div><p className="text-[10px] text-[#8b949e]">Total Signals</p><p className="font-mono text-2xl font-bold">{items.length}</p></div>
              <div><p className="text-[10px] text-[#8b949e]">Bullish</p><p className="font-mono text-2xl font-bold text-[#3fb950]">{bullish}</p></div>
              <div><p className="text-[10px] text-[#8b949e]">Bearish</p><p className="font-mono text-2xl font-bold text-[#f85149]">{bearish}</p></div>
            </div>
          </div>
          <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-2">
            {donut.length > 0 ? (
              <ResponsiveContainer width="100%" height={100}>
                <PieChart><Pie data={donut} innerRadius={25} outerRadius={40} dataKey="value">{donut.map((d) => <Cell key={d.name} fill={d.color} />)}</Pie><Tooltip /></PieChart>
              </ResponsiveContainer>
            ) : <p className="py-8 text-center text-xs text-[#484f58]">No data</p>}
          </div>
        </div>
      }
      filters={
        <div className="flex flex-wrap gap-2">
          {(['all', 'bullish', 'bearish'] as const).map((f) => (
            <button key={f} type="button" onClick={() => setFilter(f)} className={`rounded-md px-3 py-1.5 text-xs capitalize ${filter === f ? 'bg-[#388bfd] text-white' : 'border border-[#30363d] text-[#8b949e]'}`}>{f}</button>
          ))}
          <select value={tierF} onChange={(e) => setTierF(e.target.value)} className="rounded-md border border-[#30363d] bg-[#21262d] px-3 py-1.5 text-xs text-[#e6edf3]">
            <option value="all">All Tiers</option><option value="1">T1</option><option value="2">T2</option><option value="3">T3</option>
          </select>
        </div>
      }
    >
      <div className="overflow-x-auto rounded-xl border border-[#30363d] bg-[#161b22]">
        <table className="w-full min-w-[900px] text-sm">
          <thead><tr className="border-b border-[#30363d] text-[10px] uppercase text-[#8b949e]">
            <th className="px-3 py-2 text-left">Symbol</th><th className="px-3 py-2 text-left">Trend H1</th><th className="px-3 py-2 text-left">Momentum</th>
            <th className="px-3 py-2 text-left">Volume</th><th className="px-3 py-2 text-left">Score</th><th className="px-3 py-2 text-left">Dir</th><th className="px-3 py-2 text-left">Tier</th>
          </tr></thead>
          <tbody>
            {filtered.map((item) => (
              <ClickableRow key={item.id} opp={item} tint={item.direction === 'LONG' ? 'bg-[#3fb950]/5' : 'bg-[#f85149]/5'}>
                <td className="px-3 py-2 font-mono font-semibold">{pairLabel(item.symbol)}</td>
                <td className="px-3 py-2 font-mono text-xs">{formatNumber(item.scores.trend)}</td>
                <td className="px-3 py-2 font-mono text-xs">{formatNumber(item.scores.momentum)}</td>
                <td className="px-3 py-2 font-mono text-xs">{formatNumber(item.scores.volume)}</td>
                <td className="px-3 py-2 font-mono font-bold" style={{ color: scoreCircleColor(item.total_score) }}>{item.total_score}</td>
                <td className="px-3 py-2 font-mono text-xs" style={{ color: directionColor(item.direction) }}>{item.direction}</td>
                <td className="px-3 py-2"><span className="font-mono text-[10px] font-bold" style={{ color: tierColor(item.tier ?? 3) }}>T{item.tier ?? '?'}</span></td>
              </ClickableRow>
            ))}
          </tbody>
        </table>
      </div>
    </ScannerPageLayout>
  )
}
