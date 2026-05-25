import { useState } from 'react'
import { Eye, Inbox } from 'lucide-react'
import type { Opportunity } from '../../types/api'
import {
  directionColor,
  gradeColor,
  gradeLabel,
  scoreCircleColor,
  tierColor,
} from '../../utils/colors'
import {
  contextFunding,
  contextPrice,
  contextSpread,
  contextVolume,
  formatNumber,
  pairLabel,
} from '../../utils/format'
import { ScoreBreakdownModal } from '../ScoreBreakdownModal'

interface Props {
  items: Opportunity[]
  loading: boolean
}

function ScoreCircle({ score }: { score: number }) {
  const color = scoreCircleColor(score)
  const circumference = 2 * Math.PI * 16
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="relative flex h-10 w-10 items-center justify-center">
      <svg className="-rotate-90" width="40" height="40">
        <circle cx="20" cy="20" r="16" fill="none" stroke="#21262d" strokeWidth="3" />
        <circle
          cx="20"
          cy="20"
          r="16"
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute font-mono text-[10px] font-bold" style={{ color }}>
        {score}
      </span>
    </div>
  )
}

function TierBadge({ tier }: { tier: number | null | undefined }) {
  if (tier == null) {
    return <span className="text-xs text-[#484f58]">—</span>
  }
  const color = tierColor(tier)
  const bg = tier === 1 ? 'bg-[#3fb950]/15' : tier === 2 ? 'bg-[#d29922]/15' : 'bg-[#484f58]/20'
  return (
    <span
      className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold ${bg}`}
      style={{ color }}
    >
      T{tier}
    </span>
  )
}

function cellOrScore(contextVal: string, scoreVal: number | null | undefined): string {
  if (contextVal !== '—') return contextVal
  if (scoreVal != null) return formatNumber(scoreVal, 0)
  return '—'
}

export function OpportunitiesTable({ items, loading }: Props) {
  const [selected, setSelected] = useState<Opportunity | null>(null)

  if (loading && items.length === 0) {
    return (
      <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-12 text-center">
        <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-[#388bfd] border-t-transparent" />
        <p className="text-sm text-[#8b949e]">Loading opportunities…</p>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-12 text-center">
        <Inbox className="mx-auto mb-3 h-10 w-10 text-[#484f58]" />
        <p className="text-sm font-medium text-[#e6edf3]">No opportunities yet</p>
        <p className="mt-1 text-xs text-[#8b949e]">
          The scanner is running — approved opportunities will appear here automatically.
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="overflow-hidden rounded-xl border border-[#30363d] bg-[#161b22]">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[980px] text-left text-sm">
            <thead>
              <tr className="border-b border-[#30363d] bg-[#0d1117]/50 text-[10px] uppercase tracking-wider text-[#8b949e]">
                <th className="px-4 py-3 font-semibold">#</th>
                <th className="px-4 py-3 font-semibold">Pair</th>
                <th className="px-4 py-3 font-semibold">Entry</th>
                <th className="px-4 py-3 font-semibold">Strategy</th>
                <th className="px-4 py-3 font-semibold">Direction</th>
                <th className="px-4 py-3 font-semibold">Score</th>
                <th className="px-4 py-3 font-semibold">Tier</th>
                <th className="px-4 py-3 font-semibold">Trend H1</th>
                <th className="px-4 py-3 font-semibold">Momentum M15</th>
                <th className="px-4 py-3 font-semibold">Funding</th>
                <th className="px-4 py-3 font-semibold">Volume</th>
                <th className="px-4 py-3 font-semibold">Spread</th>
                <th className="px-4 py-3 font-semibold" />
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => {
                const grade = gradeLabel(item.grade, item.total_score)
                const gradeClr = gradeColor(item.grade, item.total_score)
                const funding = contextFunding(item.context)
                const volume = contextVolume(item.context)
                const spread = contextSpread(item.context)
                return (
                  <tr
                    key={item.id}
                    className="cursor-pointer border-b border-[#21262d] transition-colors hover:bg-[#21262d]/50"
                    onClick={() => setSelected(item)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-[#8b949e]">{idx + 1}</td>
                    <td className="px-4 py-3">
                      <span className="font-mono font-semibold text-[#e6edf3]">
                        {pairLabel(item.symbol)}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[#e6edf3]">
                      {contextPrice(item.context)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                          item.strategy === 'FUNDING'
                            ? 'bg-[#f85149]/15 text-[#f85149]'
                            : 'bg-[#388bfd]/15 text-[#388bfd]'
                        }`}
                      >
                        {item.strategy}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="font-mono text-xs font-bold"
                        style={{ color: directionColor(item.direction) }}
                      >
                        {item.direction}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <ScoreCircle score={item.total_score} />
                        <span className="text-[10px] font-bold" style={{ color: gradeClr }}>
                          {grade}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <TierBadge tier={item.tier} />
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[#8b949e]">
                      {formatNumber(item.scores.trend)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[#8b949e]">
                      {formatNumber(item.scores.momentum)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[#8b949e]">
                      {cellOrScore(funding, item.scores.funding)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[#8b949e]">
                      {cellOrScore(volume, item.scores.volume)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[#8b949e]">
                      {cellOrScore(spread, item.scores.spread)}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelected(item)
                        }}
                        className="flex items-center gap-1 rounded-md border border-[#30363d] px-2 py-1 text-[10px] text-[#8b949e] hover:border-[#388bfd] hover:text-[#388bfd]"
                      >
                        <Eye className="h-3 w-3" />
                        Watch
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <ScoreBreakdownModal opportunity={selected} onClose={() => setSelected(null)} />
      )}
    </>
  )
}
