import { Inbox, RefreshCw } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useTranslation } from '../../i18n/I18nProvider'
import { ScoreBreakdownModal } from '../ScoreBreakdownModal'
import type { Opportunity } from '../../types/api'

interface Props {
  title: string
  icon: ReactNode
  loading: boolean
  error: string | null
  onRefresh: () => void
  header?: ReactNode
  filters?: ReactNode
  children: ReactNode
  items: Opportunity[]
  emptyTitle?: string
  emptyDesc?: string
}

export function ScannerPageLayout({
  title,
  icon,
  loading,
  error,
  onRefresh,
  header,
  filters,
  children,
  items,
  emptyTitle,
  emptyDesc,
}: Props) {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<Opportunity | null>(null)

  const resolvedEmptyTitle = emptyTitle ?? t('scanner.noSignals')
  const resolvedEmptyDesc = emptyDesc ?? t('scanner.noSignalsDesc')

  return (
    <div className="space-y-4 p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {icon}
          <h1 className="text-lg font-semibold text-[#e6edf3]">{title}</h1>
          <span className="font-mono text-sm text-[#8b949e]">({items.length})</span>
        </div>
        <button
          type="button"
          onClick={() => void onRefresh()}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-[#30363d] bg-[#21262d] px-3 py-1.5 text-xs text-[#e6edf3] hover:bg-[#30363d] disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-[#f85149]/30 bg-[#f85149]/10 px-4 py-3 text-sm text-[#f85149]">
          {error}
        </div>
      )}

      {header}

      {filters}

      {loading && items.length === 0 ? (
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-12 text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-[#388bfd] border-t-transparent" />
          <p className="text-sm text-[#8b949e]">{t('common.loading')}</p>
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-12 text-center">
          <Inbox className="mx-auto mb-3 h-10 w-10 text-[#484f58]" />
          <p className="text-sm font-medium text-[#e6edf3]">{resolvedEmptyTitle}</p>
          <p className="mt-1 text-xs text-[#8b949e]">{resolvedEmptyDesc}</p>
        </div>
      ) : (
        <div onClick={(e) => {
          const row = (e.target as HTMLElement).closest('[data-opp-id]')
          if (row) {
            const id = Number(row.getAttribute('data-opp-id'))
            const opp = items.find((i) => i.id === id)
            if (opp) setSelected(opp)
          }
        }}
        >
          {children}
        </div>
      )}

      {selected && (
        <ScoreBreakdownModal opportunity={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}

export function ClickableRow({
  opp,
  children,
  tint,
}: {
  opp: Opportunity
  children: ReactNode
  tint?: string
}) {
  return (
    <tr
      data-opp-id={opp.id}
      className={`cursor-pointer border-b border-[#21262d] transition-colors hover:bg-[#21262d]/60 ${tint ?? ''}`}
    >
      {children}
    </tr>
  )
}
