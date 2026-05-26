import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  CheckCircle2,
  Inbox,
  Loader2,
  XCircle,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { TradeDetailModal } from './TradeDetailModal'
import { useTranslation } from '../../i18n/I18nProvider'
import type { Opportunity, PaperTrade } from '../../types/api'
import { directionColor, gradeColor, gradeLabel, scoreCircleColor } from '../../utils/colors'
import {
  formatDateTimeShort,
  formatDuration,
  formatPctColored,
  formatPercent,
  formatPrice,
  pairLabel,
} from '../../utils/format'

type SortField =
  | 'entry_at'
  | 'symbol'
  | 'strategy_type'
  | 'direction'
  | 'entry_price'
  | 'pnl_pct'
  | 'status'
type SortDir = 'asc' | 'desc'

interface TradesTableProps {
  items: PaperTrade[]
  opportunityMap: Map<number, Opportunity>
  loading: boolean
}

function compareTrades(a: PaperTrade, b: PaperTrade, field: SortField, dir: SortDir): number {
  let cmp = 0
  switch (field) {
    case 'entry_at':
      cmp = new Date(a.entry_at).getTime() - new Date(b.entry_at).getTime()
      break
    case 'symbol':
      cmp = a.symbol.localeCompare(b.symbol)
      break
    case 'strategy_type':
      cmp = a.strategy_type.localeCompare(b.strategy_type)
      break
    case 'direction':
      cmp = a.direction.localeCompare(b.direction)
      break
    case 'entry_price':
      cmp = parseFloat(a.entry_price) - parseFloat(b.entry_price)
      break
    case 'pnl_pct':
      cmp = (a.pnl_pct ?? -999) - (b.pnl_pct ?? -999)
      break
    case 'status':
      cmp = a.status.localeCompare(b.status)
      break
  }
  return dir === 'asc' ? cmp : -cmp
}

function SortableHeader({
  label,
  field,
  sortField,
  sortDir,
  onSort,
}: {
  label: string
  field: SortField
  sortField: SortField
  sortDir: SortDir
  onSort: (field: SortField) => void
}) {
  const active = sortField === field
  return (
    <th className="px-2.5 py-2.5 font-semibold">
      <button
        type="button"
        onClick={() => onSort(field)}
        className="inline-flex items-center gap-1 uppercase tracking-wider hover:text-[#e6edf3]"
      >
        {label}
        {active ? (
          sortDir === 'asc' ? (
            <ArrowUp className="h-3 w-3 text-[#388bfd]" />
          ) : (
            <ArrowDown className="h-3 w-3 text-[#388bfd]" />
          )
        ) : (
          <ArrowUpDown className="h-3 w-3 opacity-40" />
        )}
      </button>
    </th>
  )
}

function StatusBadge({ status }: { status: PaperTrade['status'] }) {
  const { t } = useTranslation()
  const config =
    {
      RUNNING: { labelKey: 'alerts.trade.running', color: '#388bfd', icon: <Loader2 className="h-3 w-3 animate-spin" /> },
      PENDING: { labelKey: 'alerts.trade.pending', color: '#d29922', icon: <Loader2 className="h-3 w-3 animate-spin" /> },
      WIN: { labelKey: 'alerts.trade.win', color: '#3fb950', icon: <CheckCircle2 className="h-3 w-3" /> },
      LOSS: { labelKey: 'alerts.trade.loss', color: '#f85149', icon: <XCircle className="h-3 w-3" /> },
      EXPIRED: { labelKey: 'alerts.trade.expired', color: '#8b949e', icon: null },
      CANCELLED: { labelKey: 'alerts.trade.cancelled', color: '#484f58', icon: null },
      CONFIRM_FAILED: { labelKey: 'alerts.trade.failed', color: '#f85149', icon: <XCircle className="h-3 w-3" /> },
    }[status] ?? { labelKey: status, color: '#8b949e', icon: null }

  return (
    <span
      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold"
      style={{ color: config.color, backgroundColor: `${config.color}22` }}
    >
      {config.icon}
      {t(config.labelKey)}
    </span>
  )
}

function EntryTypeBadge({ trade }: { trade: PaperTrade }) {
  const { t } = useTranslation()
  const status = trade.confirmation_status

  if (status === 'INSTANT') {
    return (
      <span className="inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold text-[#39c5cf] bg-[#39c5cf]/15">
        {t('alerts.entry.instant')}
      </span>
    )
  }

  if (status === 'CONFIRMED') {
    return (
      <span className="inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold text-white bg-[#238636]">
        {t('alerts.entry.confirmed')}
      </span>
    )
  }

  if (status === 'PENDING') {
    return (
      <span className="inline-flex animate-pulse rounded px-1.5 py-0.5 text-[10px] font-bold text-[#d29922] bg-[#d29922]/20">
        {t('alerts.entry.pending')}
      </span>
    )
  }

  return (
    <span className="inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold text-[#f85149] bg-[#f85149]/15">
      {t('alerts.entry.failed')}
    </span>
  )
}

function ScoreBadge({
  trade,
  opportunity,
}: {
  trade: PaperTrade
  opportunity: Opportunity | undefined
}) {
  const totalScore = trade.total_score ?? opportunity?.total_score
  const grade = trade.grade ?? opportunity?.grade

  if (totalScore == null) {
    return <span className="text-[10px] text-[#484f58]">—</span>
  }

  const gradeLabelText = gradeLabel(grade ?? null, totalScore)
  const clr = gradeColor(grade ?? null, totalScore)
  const scoreClr = scoreCircleColor(totalScore)

  return (
    <span
      className="inline-flex flex-col items-center rounded px-1.5 py-0.5 text-[10px] font-bold leading-tight"
      style={{ color: scoreClr, backgroundColor: `${scoreClr}18` }}
      title={gradeLabelText}
    >
      <span className="font-mono">{totalScore}</span>
      <span className="text-[8px] font-normal opacity-80" style={{ color: clr }}>
        {gradeLabelText}
      </span>
    </span>
  )
}

function SlTpCell({ price, pct, variant }: { price: string; pct: number; variant: 'sl' | 'tp' }) {
  const color = variant === 'sl' ? '#f85149' : '#3fb950'
  return (
    <div className="flex flex-col">
      <span className="font-mono text-xs" style={{ color }}>
        {formatPrice(price)}
      </span>
      <span className="font-mono text-[10px] text-[#484f58]">{formatPercent(pct, 2)}</span>
    </div>
  )
}

export function TradesTable({ items, opportunityMap, loading }: TradesTableProps) {
  const { t } = useTranslation()
  const [sortField, setSortField] = useState<SortField>('entry_at')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [selectedTrade, setSelectedTrade] = useState<PaperTrade | null>(null)

  const sortedItems = useMemo(
    () => [...items].sort((a, b) => compareTrades(a, b, sortField, sortDir)),
    [items, sortField, sortDir],
  )

  const summary = useMemo(() => {
    const running = sortedItems.filter(
      (tr) => tr.status === 'RUNNING' || tr.status === 'PENDING',
    ).length
    const wins = sortedItems.filter((tr) => tr.status === 'WIN').length
    const losses = sortedItems.filter((tr) => tr.status === 'LOSS').length
    const closedWithPnl = sortedItems.filter((tr) => tr.pnl_pct != null)
    const winRate = closedWithPnl.length ? (wins / closedWithPnl.length) * 100 : 0
    const avgPnl = closedWithPnl.length
      ? closedWithPnl.reduce((sum, tr) => sum + (tr.pnl_pct ?? 0), 0) / closedWithPnl.length
      : 0
    return { total: sortedItems.length, running, wins, losses, winRate, avgPnl }
  }, [sortedItems])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDir(field === 'entry_at' ? 'desc' : 'asc')
    }
  }

  const handleRowClick = (trade: PaperTrade) => setSelectedTrade(trade)

  if (loading && sortedItems.length === 0) {
    return (
      <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-12 text-center">
        <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-[#388bfd] border-t-transparent" />
        <p className="text-sm text-[#8b949e]">{t('alerts.loadingTrades')}</p>
      </div>
    )
  }

  if (sortedItems.length === 0) {
    return (
      <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-12 text-center">
        <Inbox className="mx-auto mb-3 h-10 w-10 text-[#484f58]" />
        <p className="text-sm font-medium text-[#e6edf3]">{t('alerts.noMatch')}</p>
        <p className="mt-1 text-xs text-[#8b949e]">{t('alerts.noMatchDesc')}</p>
      </div>
    )
  }

  return (
    <>
      <div className="overflow-hidden rounded-lg border border-[#30363d] bg-[#161b22]">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1200px] text-left text-sm">
            <thead>
              <tr className="border-b border-[#30363d] bg-[#0d1117]/50 text-[10px] uppercase tracking-wider text-[#8b949e]">
                <th className="px-2.5 py-2.5 font-semibold">#</th>
                <SortableHeader label={t('alerts.col.symbol')} field="symbol" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <SortableHeader label={t('alerts.col.strategy')} field="strategy_type" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <SortableHeader label={t('alerts.col.dir')} field="direction" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <th className="px-2.5 py-2.5 font-semibold">{t('alerts.col.score')}</th>
                <SortableHeader label={t('alerts.col.entry')} field="entry_price" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <th className="px-2.5 py-2.5 font-semibold">{t('alerts.col.sl')}</th>
                <th className="px-2.5 py-2.5 font-semibold">{t('alerts.col.tp')}</th>
                <SortableHeader label={t('alerts.col.pnl')} field="pnl_pct" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <SortableHeader label={t('alerts.col.status')} field="status" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <th className="px-2.5 py-2.5 font-semibold">{t('alerts.col.entryType')}</th>
                <SortableHeader label={t('alerts.col.opened')} field="entry_at" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <th className="px-2.5 py-2.5 font-semibold">{t('alerts.col.closed')}</th>
                <th className="px-2.5 py-2.5 font-semibold">{t('alerts.col.duration')}</th>
              </tr>
            </thead>
            <tbody>
              {sortedItems.map((trade, idx) => {
                const isRunning = trade.status === 'RUNNING' || trade.status === 'PENDING'
                const pnl = isRunning ? null : formatPctColored(trade.pnl_pct)
                const duration =
                  trade.duration_seconds ??
                  (isRunning
                    ? (Date.now() - new Date(trade.entry_at).getTime()) / 1000
                    : null)
                const opp = opportunityMap.get(trade.opportunity_id)

                return (
                  <tr
                    key={trade.id}
                    onClick={() => handleRowClick(trade)}
                    className="cursor-pointer border-b border-[#21262d] transition-colors hover:bg-[#21262d]/60"
                  >
                    <td className="px-2.5 py-2 font-mono text-xs text-[#8b949e]">{idx + 1}</td>
                    <td className="px-2.5 py-2 font-mono text-xs font-semibold text-[#e6edf3]">
                      {pairLabel(trade.symbol)}
                    </td>
                    <td className="px-2.5 py-2">
                      <span className="rounded bg-[#388bfd]/15 px-1.5 py-0.5 text-[10px] font-bold text-[#388bfd]">
                        {trade.strategy_type.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-2.5 py-2">
                      <span
                        className="font-mono text-[10px] font-bold"
                        style={{ color: directionColor(trade.direction) }}
                      >
                        {trade.direction === 'LONG' ? t('alerts.long') : t('alerts.short')}
                      </span>
                    </td>
                    <td className="px-2.5 py-2">
                      <ScoreBadge trade={trade} opportunity={opp} />
                    </td>
                    <td className="px-2.5 py-2 font-mono text-xs text-[#8b949e]">
                      {formatPrice(trade.entry_price)}
                    </td>
                    <td className="px-2.5 py-2">
                      <SlTpCell price={trade.sl_price} pct={trade.sl_pct} variant="sl" />
                    </td>
                    <td className="px-2.5 py-2">
                      <SlTpCell price={trade.tp_price} pct={trade.tp_pct} variant="tp" />
                    </td>
                    <td className="px-2.5 py-2 font-mono text-xs font-bold">
                      {isRunning ? (
                        <span className="text-[#484f58]">—</span>
                      ) : (
                        <span style={{ color: pnl!.color }}>{pnl!.text}</span>
                      )}
                    </td>
                    <td className="px-2.5 py-2">
                      <StatusBadge status={trade.status} />
                    </td>
                    <td className="px-2.5 py-2">
                      <EntryTypeBadge trade={trade} />
                    </td>
                    <td className="px-2.5 py-2 font-mono text-[10px] text-[#8b949e]">
                      {formatDateTimeShort(trade.entry_at)}
                    </td>
                    <td className="px-2.5 py-2 font-mono text-[10px] text-[#8b949e]">
                      {formatDateTimeShort(trade.closed_at)}
                    </td>
                    <td className="px-2.5 py-2 font-mono text-[10px] text-[#8b949e]">
                      {formatDuration(duration)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <div className="border-t border-[#30363d] bg-[#0d1117]/50 px-4 py-2.5 text-xs text-[#8b949e]">
          {t('alerts.summaryCompact', {
            total: summary.total,
            running: summary.running,
            wins: summary.wins,
            winRate: summary.winRate.toFixed(0),
            losses: summary.losses,
          })}{' '}
          <span style={{ color: formatPctColored(summary.avgPnl).color }}>
            {formatPctColored(summary.avgPnl).text}
          </span>
        </div>
      </div>

      {selectedTrade && (
        <TradeDetailModal
          trade={selectedTrade}
          opportunity={opportunityMap.get(selectedTrade.opportunity_id)}
          onClose={() => setSelectedTrade(null)}
        />
      )}
    </>
  )
}
