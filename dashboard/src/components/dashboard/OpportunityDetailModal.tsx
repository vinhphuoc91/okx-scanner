import { X } from 'lucide-react'
import type { Opportunity } from '../../types/api'
import {
  directionColor,
  gradeColor,
  gradeLabel,
  scoreCircleColor,
  tierColor,
} from '../../utils/colors'
import { formatNumber, formatRelativeTime, pairLabel } from '../../utils/format'

interface Props {
  opportunity: Opportunity
  onClose: () => void
}

const BREAKDOWN_ROWS: { key: keyof Opportunity['scores']; label: string }[] = [
  { key: 'trend', label: 'Trend (H1)' },
  { key: 'momentum', label: 'Momentum (M15)' },
  { key: 'liquidity', label: 'Liquidity' },
  { key: 'volume', label: 'Volume' },
  { key: 'funding', label: 'Funding' },
  { key: 'spread', label: 'Spread' },
  { key: 'risk_penalty', label: 'Risk Penalty' },
]

export function OpportunityDetailModal({ opportunity, onClose }: Props) {
  const grade = gradeLabel(opportunity.grade, opportunity.total_score)
  const gradeClr = gradeColor(opportunity.grade, opportunity.total_score)
  const scoreClr = scoreCircleColor(opportunity.total_score)
  const tier = opportunity.tier
  const tierClr = tier != null ? tierColor(tier) : '#8b949e'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
      role="presentation"
    >
      <div
        className="w-full max-w-md rounded-xl border border-[#30363d] bg-[#161b22] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="opp-detail-title"
      >
        <div className="flex items-center justify-between border-b border-[#30363d] px-5 py-4">
          <div>
            <h2 id="opp-detail-title" className="font-mono text-lg font-bold text-[#e6edf3]">
              {pairLabel(opportunity.symbol)}
            </h2>
            <p className="text-xs text-[#8b949e]">
              {formatRelativeTime(opportunity.detected_at)} · {opportunity.strategy}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-[#8b949e] hover:bg-[#21262d] hover:text-[#e6edf3]"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-5 py-4">
          <div className="mb-5 flex items-center gap-4">
            <div
              className="flex h-16 w-16 items-center justify-center rounded-full border-4 font-mono text-xl font-bold"
              style={{ borderColor: scoreClr, color: scoreClr }}
            >
              {opportunity.total_score}
            </div>
            <div>
              <p className="text-sm font-bold" style={{ color: gradeClr }}>
                {grade}
              </p>
              <p
                className="font-mono text-xs font-bold"
                style={{ color: directionColor(opportunity.direction) }}
              >
                {opportunity.direction}
              </p>
              {tier != null && (
                <span
                  className="mt-1 inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold"
                  style={{ color: tierClr, backgroundColor: tierClr + '22' }}
                >
                  Tier {tier}
                </span>
              )}
            </div>
          </div>

          <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-[#8b949e]">
            Score Breakdown
          </h3>
          <ul className="space-y-2">
            {BREAKDOWN_ROWS.map(({ key, label }) => {
              const raw = opportunity.scores[key]
              const display = formatNumber(raw as number | null, 1)
              return (
                <li
                  key={key}
                  className="flex items-center justify-between rounded-lg bg-[#0d1117] px-3 py-2"
                >
                  <span className="text-xs text-[#8b949e]">{label}</span>
                  <span className="font-mono text-sm font-semibold text-[#e6edf3]">{display}</span>
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </div>
  )
}
