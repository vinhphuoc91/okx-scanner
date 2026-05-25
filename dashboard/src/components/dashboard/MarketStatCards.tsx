import { Bitcoin, DollarSign, Flame, Gauge, TrendingUp } from 'lucide-react'
import type { Opportunity, StatsResponse, StatusResponse } from '../../types/api'
import { formatNumber } from '../../utils/format'

interface Props {
  opportunities: Opportunity[]
  stats: StatsResponse | null
  status: StatusResponse | null
}

export function MarketStatCards({ opportunities, stats, status }: Props) {
  const avgScore =
    opportunities.length > 0
      ? opportunities.reduce((s, o) => s + o.total_score, 0) / opportunities.length
      : null

  const fundingHigh = opportunities.filter((o) => (o.scores.funding ?? 0) >= 30).length
  const fundingTotal = stats?.by_strategy.funding ?? 0

  const sentiment = avgScore ?? 50
  const sentimentLabel =
    sentiment >= 75 ? 'Bullish' : sentiment >= 60 ? 'Neutral' : 'Cautious'
  const sentimentColor =
    sentiment >= 75 ? '#3fb950' : sentiment >= 60 ? '#d29922' : '#f85149'

  const scanned = status?.worker_totals?.total_scanned ?? status?.worker_totals?.scanned ?? 0

  const cards = [
    {
      icon: <DollarSign className="h-4 w-4 text-[#388bfd]" />,
      label: 'Approved Today',
      value: stats ? formatNumber(stats.total_today) : '—',
      sub: 'opportunities detected',
    },
    {
      icon: <TrendingUp className="h-4 w-4 text-[#3fb950]" />,
      label: '24h Scan Volume',
      value: scanned > 0 ? formatNumber(scanned) : '—',
      sub: 'instruments scanned',
    },
    {
      icon: <Bitcoin className="h-4 w-4 text-[#d29922]" />,
      label: 'Avg Score',
      value: avgScore != null ? avgScore.toFixed(1) : '—',
      sub: 'across approved set',
    },
    {
      icon: <Flame className="h-4 w-4 text-[#f85149]" />,
      label: 'Funding Signals',
      value: formatNumber(fundingTotal || fundingHigh),
      sub: 'funding strategy today',
    },
    {
      icon: <Gauge className="h-4 w-4" style={{ color: sentimentColor }} />,
      label: 'Market Sentiment',
      value: sentimentLabel,
      sub: avgScore != null ? `avg ${avgScore.toFixed(0)}/100` : 'no data yet',
      accent: sentimentColor,
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-xl border border-[#30363d] bg-[#161b22] p-4 transition-colors hover:border-[#484f58]"
        >
          <div className="mb-3 flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#8b949e]">
              {card.label}
            </span>
            {card.icon}
          </div>
          <p
            className="font-mono text-2xl font-bold text-[#e6edf3]"
            style={card.accent ? { color: card.accent } : undefined}
          >
            {card.value}
          </p>
          <p className="mt-1 text-[11px] text-[#484f58]">{card.sub}</p>
          {card.label === 'Market Sentiment' && avgScore != null && (
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#21262d]">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, avgScore)}%`, backgroundColor: sentimentColor }}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
