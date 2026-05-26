import { X } from 'lucide-react'
import { useState } from 'react'
import type { Opportunity, PaperTrade } from '../../types/api'
import { directionColor, scoreCircleColor } from '../../utils/colors'
import { formatDateTimeShort, formatDuration, formatPercent, formatPrice, pairLabel } from '../../utils/format'

function toTVSymbol(symbol: string): string {
  return 'OKX:' + symbol.replace(/-SWAP$/, '').replace(/-/g, '') + '.P'
}

interface Props {
  trade: PaperTrade
  opportunity?: Opportunity
  onClose: () => void
}

export function TradeDetailModal({ trade, opportunity, onClose }: Props) {
  const [tab, setTab] = useState<'info' | 'chart'>('info')
  const isRunning = trade.status === 'RUNNING'
  const duration = trade.duration_seconds ?? (isRunning ? (Date.now() - new Date(trade.entry_at).getTime()) / 1000 : null)
  const ctx = opportunity?.context ?? {}

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose} role="presentation">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-[#30363d] bg-[#161b22] shadow-2xl"
        onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">

        {/* Header */}
        <div className="sticky top-0 border-b border-[#30363d] bg-[#161b22] px-5 pt-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-mono text-lg font-bold text-[#e6edf3]">{pairLabel(trade.symbol)}</h2>
              <p className="text-xs text-[#8b949e]">
                {trade.strategy_type} ·{' '}
                <span style={{ color: directionColor(trade.direction) }}>{trade.direction}</span>
                {' · '}{trade.status}
              </p>
            </div>
            <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-[#8b949e] hover:bg-[#21262d]">
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="flex gap-1 pb-3 pt-2">
            {(['info', 'chart'] as const).map((t) => (
              <button key={t} type="button" onClick={() => setTab(t)}
                className={`rounded px-3 py-1 text-xs font-medium ${tab === t ? 'bg-[#388bfd] text-white' : 'text-[#8b949e] hover:text-[#e6edf3]'}`}>
                {t === 'info' ? '📋 Info' : '📈 Chart'}
              </button>
            ))}
          </div>
        </div>

        {tab === 'info' && (
          <div className="space-y-4 p-5">
            {/* Trade stats */}
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: 'Entry', value: formatPrice(trade.entry_price) },
                { label: 'SL', value: formatPrice(trade.sl_price), sub: formatPercent(trade.sl_pct, 2), color: '#f85149' },
                { label: 'TP', value: formatPrice(trade.tp_price), sub: formatPercent(trade.tp_pct, 2), color: '#3fb950' },
                { label: 'Opened', value: formatDateTimeShort(trade.entry_at) },
                { label: 'Duration', value: formatDuration(duration) },
                { label: 'P&L', value: trade.pnl_pct != null ? `${trade.pnl_pct > 0 ? '+' : ''}${trade.pnl_pct.toFixed(2)}%` : '—',
                  color: trade.pnl_pct != null ? (trade.pnl_pct >= 0 ? '#3fb950' : '#f85149') : undefined },
              ].map((item) => (
                <div key={item.label} className="rounded-lg bg-[#0d1117] px-3 py-2">
                  <p className="text-[10px] uppercase text-[#8b949e]">{item.label}</p>
                  <p className="font-mono text-sm font-bold" style={{ color: item.color ?? '#e6edf3' }}>{item.value}</p>
                  {item.sub && <p className="font-mono text-[10px] text-[#484f58]">{item.sub}</p>}
                </div>
              ))}
            </div>

            {/* Score */}
            {opportunity && (
              <div className="flex items-center gap-3 rounded-lg bg-[#0d1117] p-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-4 font-mono text-lg font-bold"
                  style={{ borderColor: scoreCircleColor(opportunity.total_score), color: scoreCircleColor(opportunity.total_score) }}>
                  {opportunity.total_score}
                </div>
                <div className="text-xs text-[#8b949e]">Signal score at detection · {formatDateTimeShort(opportunity.detected_at)}</div>
              </div>
            )}

            {/* Signal context */}
            {Object.keys(ctx).length > 0 && (
              <div>
                <h3 className="mb-2 text-[10px] font-semibold uppercase text-[#8b949e]">Why this trade?</h3>
                <div className="max-h-48 overflow-y-auto rounded-lg bg-[#0d1117] p-3">
                  {Object.entries(ctx).map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-2 py-0.5 text-[11px]">
                      <span className="text-[#8b949e]">{k}</span>
                      <span className="truncate font-mono text-[#e6edf3]">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {tab === 'chart' && (
          <div className="p-4">
            <iframe
              key={trade.symbol}
              src={`https://www.tradingview.com/widgetembed/?symbol=${toTVSymbol(trade.symbol)}&interval=15&theme=dark&style=1&locale=en&hide_side_toolbar=0&allow_symbol_change=0`}
              className="w-full rounded-lg border border-[#30363d]"
              style={{ height: '450px' }}
              title="TradingView Chart"
            />
            <p className="mt-2 text-center text-[10px] text-[#8b949e]">M15 · {toTVSymbol(trade.symbol)}</p>
          </div>
        )}
      </div>
    </div>
  )
}
