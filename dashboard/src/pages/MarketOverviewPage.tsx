import { BarChart3 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { ScoreBreakdownModal } from '../components/ScoreBreakdownModal'
import { useAllOpportunities } from '../hooks/useStrategyOpportunities'
import type { Opportunity } from '../types/api'
import { scoreCircleColor } from '../utils/colors'
import { formatVolume, pairLabel } from '../utils/format'

export function MarketOverviewPage() {
  const { items, loading, error, refresh } = useAllOpportunities()
  const [selected, setSelected] = useState<Opportunity | null>(null)

  const totalVol = useMemo(
    () => items.reduce((s, i) => s + parseFloat(String(i.context?.volume_24h_usd ?? i.scores.volume ?? 0)), 0),
    [items],
  )

  const fundingRates = items
    .filter((i) => i.context?.funding_rate)
    .map((i) => parseFloat(String(i.context!.funding_rate)) * 100)

  const heatmap = [...items].slice(0, 50)
  const gainers = [...items].sort((a, b) => b.total_score - a.total_score).slice(0, 10)
  const losers = [...items].sort((a, b) => a.total_score - b.total_score).slice(0, 10)

  const byStrategy = useMemo(
    () =>
      Object.entries(
        items.reduce<Record<string, number>>((acc, i) => {
          acc[i.strategy] = (acc[i.strategy] ?? 0) + 1
          return acc
        }, {}),
      ).map(([name, value]) => ({ name, value })),
    [items],
  )

  const statCards = useMemo(
    () => [
      { label: 'Active Signals', value: String(items.length) },
      {
        label: 'Est. 24h Volume',
        value: formatVolume(totalVol),
      },
      { label: 'Strategies Active', value: String(byStrategy.length) },
      {
        label: 'Avg Score',
        value: items.length
          ? (items.reduce((s, i) => s + i.total_score, 0) / items.length).toFixed(1)
          : '—',
      },
    ],
    [items, totalVol, byStrategy.length],
  )

  if (loading && items.length === 0) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center p-6">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#388bfd] border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-4 p-4 sm:p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-[#388bfd]" />
          <h1 className="text-lg font-semibold text-[#e6edf3]">Market Overview</h1>
        </div>
        <button type="button" onClick={() => void refresh()} className="text-xs text-[#388bfd]">Refresh</button>
      </div>
      {error && <p className="text-sm text-[#f85149]">{error}</p>}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {statCards.map((c) => (
          <div key={c.label} className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
            <p className="text-[10px] uppercase text-[#8b949e]">{c.label}</p>
            <p className="font-mono text-xl font-bold text-[#e6edf3]">{c.value}</p>
          </div>
        ))}
      </div>

      {heatmap.length > 0 && (
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase text-[#8b949e]">Signal Heatmap (by score)</h3>
          <div className="grid grid-cols-5 gap-1 sm:grid-cols-10">
            {heatmap.map((item) => {
              const c = item.total_score >= 75 ? '#3fb950' : item.total_score >= 65 ? '#d29922' : '#f85149'
              return (
                <button key={item.id} type="button" onClick={() => setSelected(item)}
                  className="rounded p-1.5 text-center hover:scale-105" style={{ backgroundColor: c + '33', border: `1px solid ${c}55` }}>
                  <p className="truncate text-[8px] font-mono">{pairLabel(item.symbol).split('/')[0]}</p>
                  <p className="font-mono text-[9px] font-bold" style={{ color: c }}>{item.total_score}</p>
                </button>
              )
            })}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase text-[#3fb950]">Top Gainers (Score)</h3>
          <table className="w-full text-xs"><tbody>
            {gainers.map((i) => (
              <tr key={i.id} className="cursor-pointer border-b border-[#21262d] hover:bg-[#21262d]/50" onClick={() => setSelected(i)}>
                <td className="py-1.5 font-mono">{pairLabel(i.symbol)}</td>
                <td className="py-1.5 font-mono font-bold" style={{ color: scoreCircleColor(i.total_score) }}>{i.total_score}</td>
              </tr>
            ))}
          </tbody></table>
        </div>
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase text-[#f85149]">Lowest Scores</h3>
          <table className="w-full text-xs"><tbody>
            {losers.map((i) => (
              <tr key={i.id} className="cursor-pointer border-b border-[#21262d] hover:bg-[#21262d]/50" onClick={() => setSelected(i)}>
                <td className="py-1.5 font-mono">{pairLabel(i.symbol)}</td>
                <td className="py-1.5 font-mono font-bold" style={{ color: scoreCircleColor(i.total_score) }}>{i.total_score}</td>
              </tr>
            ))}
          </tbody></table>
        </div>
      </div>

      {fundingRates.length > 0 && (
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase text-[#8b949e]">Funding Distribution</h3>
          <ResponsiveContainer width="100%" height={120}>
            <PieChart>
              <Pie data={byStrategy} dataKey="value" nameKey="name" innerRadius={30} outerRadius={50}>
                {byStrategy.map((_, idx) => <Cell key={idx} fill={['#f85149', '#388bfd', '#d29922', '#3fb950', '#8b949e'][idx % 5]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {items.length === 0 && !loading && (
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-12 text-center text-sm text-[#8b949e]">
          No market data yet — waiting for scanner signals.
        </div>
      )}

      {selected && <ScoreBreakdownModal opportunity={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
