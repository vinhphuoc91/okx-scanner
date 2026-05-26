import { X } from 'lucide-react'
import { useState } from 'react'
import type { Opportunity } from '../types/api'
import {
  directionColor,
  gradeColor,
  gradeLabel,
  scoreCircleColor,
  tierColor,
} from '../utils/colors'
import { formatContextValue, formatNumber, formatRelativeTime, pairLabel } from '../utils/format'

interface Props {
  opportunity: Opportunity
  onClose: () => void
}

const SCORE_BARS: { key: keyof Opportunity['scores']; label: string; max: number }[] = [
  { key: 'trend', label: 'Trend', max: 30 },
  { key: 'momentum', label: 'Momentum', max: 25 },
  { key: 'liquidity', label: 'Liquidity', max: 25 },
  { key: 'volume', label: 'Volume', max: 20 },
  { key: 'funding', label: 'Funding', max: 40 },
  { key: 'spread', label: 'Spread', max: 20 },
]

function toTVSymbol(symbol: string): string {
  return 'OKX:' + symbol.replace(/-SWAP$/, '').replace(/-/g, '') + '.P'
}

export function ScoreBreakdownModal({ opportunity, onClose }: Props) {
  const [tab, setTab] = useState<'score' | 'chart'>('score')
  const grade = gradeLabel(opportunity.grade, opportunity.total_score)
  const gradeClr = gradeColor(opportunity.grade, opportunity.total_score)
  const scoreClr = scoreCircleColor(opportunity.total_score)
  const ctx = opportunity.context ?? {}

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-[#30363d] bg-[#161b22] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="sticky top-0 border-b border-[#30363d] bg-[#161b22]">
          <div className="flex items-center justify-between px-5 py-4">
            <div>
              <h2 className="font-mono text-lg font-bold text-[#e6edf3]">
                {pairLabel(opportunity.symbol)}
              </h2>
              <p className="text-xs text-[#8b949e]">
                {opportunity.strategy} · {formatRelativeTime(opportunity.detected_at)}
              </p>
            </div>
            <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-[#8b949e] hover:bg-[#21262d]">
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="flex gap-1 px-5 pb-3">
            {(['score', 'chart'] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`rounded px-3 py-1 text-xs font-medium ${tab === t ? 'bg-[#388bfd] text-white' : 'text-[#8b949e] hover:text-[#e6edf3]'}`}
              >
                {t === 'score' ? '📊 Score' : '📈 Chart'}
              </button>
            ))}
          </div>
        </div>

        {tab === 'score' && (
        <div className="space-y-5 p-5">
          <div className="flex items-center gap-4">
            <div
              className="flex h-14 w-14 items-center justify-center rounded-full border-4 font-mono text-xl font-bold"
              style={{ borderColor: scoreClr, color: scoreClr }}
            >
              {opportunity.total_score}
            </div>
            <div>
              <p className="text-sm font-bold" style={{ color: gradeClr }}>{grade}</p>
              <p className="font-mono text-xs font-bold" style={{ color: directionColor(opportunity.direction) }}>
                {opportunity.direction}
              </p>
              {opportunity.tier != null && (
                <span
                  className="mt-1 inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold"
                  style={{ color: tierColor(opportunity.tier), backgroundColor: tierColor(opportunity.tier) + '22' }}
                >
                  T{opportunity.tier}
                </span>
              )}
            </div>
          </div>

          <div>
            <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-[#8b949e]">
              Score Components
            </h3>
            <ul className="space-y-2">
              {SCORE_BARS.map(({ key, label, max }) => {
                const raw = opportunity.scores[key]
                const val = raw ?? 0
                const pct = Math.min(100, (val / max) * 100)
                return (
                  <li key={String(key)}>
                    <div className="mb-1 flex justify-between text-xs">
                      <span className="text-[#8b949e]">{label}</span>
                      <span className="font-mono text-[#e6edf3]">
                        {formatNumber(raw as number | null, 1)}
                      </span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-[#21262d]">
                      <div className="h-full rounded-full bg-[#388bfd]" style={{ width: `${pct}%` }} />
                    </div>
                  </li>
                )
              })}
              <li>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-[#8b949e]">Risk Penalty</span>
                  <span className="font-mono text-[#f85149]">
                    {formatNumber(opportunity.scores.risk_penalty as number | null, 1)}
                  </span>
                </div>
              </li>
            </ul>
          </div>

          {Object.keys(ctx).length > 0 && (
            <div>
              <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-[#8b949e]">
                Raw Signals
              </h3>
              <div className="max-h-40 overflow-y-auto rounded-lg bg-[#0d1117] p-3">
                {Object.entries(ctx).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2 py-0.5 text-[11px]">
                    <span className="text-[#8b949e]">{k}</span>
                    <span className="truncate font-mono text-[#e6edf3]">{formatContextValue(k, v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-lg border border-[#3fb950]/30 bg-[#3fb950]/10 px-3 py-2 text-xs text-[#3fb950]">
            Risk decision: APPROVED
          </div>
        </div>
        )}

        {tab === 'chart' && (
          <div className="p-4">
            <iframe
              key={opportunity.symbol}
              src={`https://www.tradingview.com/widgetembed/?symbol=${toTVSymbol(opportunity.symbol)}&interval=15&theme=dark&style=1&locale=en&hide_side_toolbar=0&allow_symbol_change=0`}
              className="w-full rounded-lg border border-[#30363d]"
              style={{ height: '450px' }}
              title="TradingView Chart"
            />
            <p className="mt-2 text-center text-[10px] text-[#8b949e]">
              M15 chart · {toTVSymbol(opportunity.symbol)}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
