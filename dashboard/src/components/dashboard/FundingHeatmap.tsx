import type { Opportunity } from '../../types/api'
import { pairLabel } from '../../utils/format'

interface Props {
  opportunities: Opportunity[]
  loading: boolean
}

function heatColor(value: number): string {
  if (value >= 35) return '#3fb950'
  if (value >= 25) return '#d29922'
  if (value >= 15) return '#388bfd'
  if (value > 0) return '#484f58'
  return '#21262d'
}

export function FundingHeatmap({ opportunities, loading }: Props) {
  const fundingItems = opportunities
    .filter((o) => o.strategy === 'FUNDING' || (o.scores.funding ?? 0) > 0)
    .sort((a, b) => (b.scores.funding ?? 0) - (a.scores.funding ?? 0))
    .slice(0, 20)

  return (
    <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-[#8b949e]">
        Funding Rate Heatmap
      </h3>
      {loading && fundingItems.length === 0 ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#388bfd] border-t-transparent" />
        </div>
      ) : fundingItems.length === 0 ? (
        <div className="flex h-40 items-center justify-center text-sm text-[#484f58]">
          No funding signals
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-1.5 sm:grid-cols-5">
          {fundingItems.map((item) => {
            const val = item.scores.funding ?? 0
            return (
              <div
                key={item.id}
                title={`${item.symbol}: ${val.toFixed(1)}`}
                className="group relative flex flex-col items-center rounded-md p-2 transition-transform hover:scale-105"
                style={{ backgroundColor: heatColor(val) + '33', border: `1px solid ${heatColor(val)}55` }}
              >
                <span className="truncate text-[9px] font-mono text-[#e6edf3]">
                  {pairLabel(item.symbol).split('/')[0]}
                </span>
                <span className="font-mono text-[10px] font-bold" style={{ color: heatColor(val) }}>
                  {val.toFixed(0)}
                </span>
              </div>
            )
          })}
        </div>
      )}
      <div className="mt-3 flex items-center gap-2 text-[9px] text-[#484f58]">
        <span>Low</span>
        <div className="flex flex-1 gap-0.5">
          {['#21262d', '#484f58', '#388bfd', '#d29922', '#3fb950'].map((c) => (
            <div key={c} className="h-1.5 flex-1 rounded-sm" style={{ background: c }} />
          ))}
        </div>
        <span>High</span>
      </div>
    </div>
  )
}
