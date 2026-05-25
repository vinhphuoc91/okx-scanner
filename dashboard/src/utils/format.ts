import {
  formatDateTime,
  formatFunding,
  formatPctColored,
} from './formatters'

export {
  formatATR,
  formatDateTime,
  formatDuration,
  formatFunding,
  formatPct,
  formatPctColored,
  formatPrice,
  formatSpread,
  formatVolume,
  formatContextValue,
  contextFunding,
  contextPrice,
  contextSpread,
  contextVolume,
} from './formatters'

export function formatDateTimeShort(iso: string | null | undefined): string {
  return formatDateTime(iso)
}

export function formatPnl(value: number | null | undefined): { text: string; color: string } {
  return formatPctColored(value, 2)
}

export function formatNumber(value: number | null | undefined, decimals = 0): string {
  if (value == null || Number.isNaN(value)) return '—'
  return value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

export function formatPercent(value: number | null | undefined, decimals = 2): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${value.toFixed(decimals)}%`
}

export function formatFundingRate(value: number | null | undefined): string {
  return formatFunding(value)
}

export function formatUptime(seconds: number | null | undefined): string {
  if (seconds == null) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  const diff = Date.now() - date.getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return date.toLocaleDateString()
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function pairLabel(symbol: string): string {
  return symbol.replace('-SWAP', '').replace('-USDT', '/USDT')
}
