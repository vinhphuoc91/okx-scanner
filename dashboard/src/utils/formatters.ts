/**
 * Smart price formatter - auto-detect appropriate decimal places.
 */
export function formatPrice(value: number | string | null | undefined): string {
  if (value == null || value === '') return '—'
  const num = typeof value === 'number' ? value : parseFloat(String(value))
  if (!Number.isFinite(num) || num === 0) return '—'

  if (num >= 10_000) return num.toLocaleString('en', { maximumFractionDigits: 2 })
  if (num >= 1_000) return num.toFixed(2)
  if (num >= 100) return num.toFixed(3)
  if (num >= 1) return num.toFixed(4)
  if (num >= 0.1) return num.toFixed(5)
  if (num >= 0.01) return num.toFixed(6)
  if (num >= 0.001) return num.toFixed(7)
  if (num >= 0.0001) return num.toFixed(8)
  if (num >= 0.00001) return num.toFixed(9)
  if (num >= 0.000001) return num.toFixed(10)
  return num.toExponential(4)
}

/** Format % change with +/- sign. */
export function formatPct(value: number | string | null | undefined, decimals = 2): string {
  if (value == null || value === '') return '—'
  const num = typeof value === 'number' ? value : parseFloat(String(value))
  if (!Number.isFinite(num)) return '—'
  const sign = num >= 0 ? '+' : ''
  return `${sign}${num.toFixed(decimals)}%`
}

/** Format P&L % with color for UI. */
export function formatPctColored(
  value: number | null | undefined,
  decimals = 2,
): { text: string; color: string } {
  if (value == null || !Number.isFinite(value)) return { text: '—', color: '#8b949e' }
  return {
    text: formatPct(value, decimals),
    color: value >= 0 ? '#3fb950' : '#f85149',
  }
}

/** Format large volume / market cap: $1.23B, $456.7M, $12.3K */
export function formatVolume(value: number | string | null | undefined): string {
  if (value == null || value === '') return '—'
  const num = typeof value === 'number' ? value : parseFloat(String(value))
  if (!Number.isFinite(num) || num === 0) return '—'
  if (num >= 1_000_000_000) return `$${(num / 1_000_000_000).toFixed(2)}B`
  if (num >= 1_000_000) return `$${(num / 1_000_000).toFixed(2)}M`
  if (num >= 1_000) return `$${(num / 1_000).toFixed(1)}K`
  return `$${num.toFixed(2)}`
}

/** Format funding rate decimal: +0.0123% / -0.0045% */
export function formatFunding(value: number | string | null | undefined): string {
  if (value == null || value === '') return '—'
  const num = typeof value === 'number' ? value : parseFloat(String(value))
  if (!Number.isFinite(num) || num === 0) return '—'
  const pct = num * 100
  const sign = pct >= 0 ? '+' : ''
  if (Math.abs(pct) >= 0.01) return `${sign}${pct.toFixed(4)}%`
  return `${sign}${pct.toFixed(6)}%`
}

/** Format spread (decimal fraction → %). */
export function formatSpread(value: number | string | null | undefined): string {
  if (value == null || value === '') return '—'
  const num = typeof value === 'number' ? value : parseFloat(String(value))
  if (!Number.isFinite(num) || num === 0) return '—'
  const pct = num * 100
  if (pct < 0.1) return `${pct.toFixed(4)}%`
  return `${pct.toFixed(3)}%`
}

/** Format datetime: 25/05 14:32 */
export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) return '—'
  const d = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${day}/${month} ${hour}:${min}`
}

/**
 * Format duration from start/end times or elapsed seconds.
 * - formatDuration(3600) → "1h"
 * - formatDuration("2026-05-25T10:00:00Z", closedAt) → "2h 15m"
 */
export function formatDuration(
  start: string | number | null | undefined,
  end: Date | string = new Date(),
): string {
  if (start == null || start === '') return '—'

  let diffMs: number
  if (typeof start === 'number') {
    if (!Number.isFinite(start) || start < 0) return '—'
    diffMs = start * 1000
  } else {
    const endDate = end instanceof Date ? end : new Date(end)
    diffMs = endDate.getTime() - new Date(start).getTime()
    if (!Number.isFinite(diffMs) || diffMs < 0) return '—'
  }

  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return '<1m'
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  if (mins === 0) return `${hours}h`
  return `${hours}h ${mins}m`
}

/** Format ATR value using smart price decimals. */
export function formatATR(value: number | string | null | undefined): string {
  return formatPrice(value)
}

/** Extract display price from opportunity context. */
export function contextPrice(context: Record<string, unknown> | undefined): string {
  if (!context) return '—'
  const raw =
    context.last_price ??
    context.ema_fast ??
    context.signal_price ??
    context.entry_price
  return formatPrice(raw as string | number)
}

export function contextVolume(context: Record<string, unknown> | undefined): string {
  if (!context?.volume_24h_usd) return '—'
  return formatVolume(context.volume_24h_usd as string | number)
}

export function contextSpread(context: Record<string, unknown> | undefined): string {
  if (!context?.spread_pct) return '—'
  return formatSpread(context.spread_pct as string | number)
}

export function formatContextValue(key: string, value: unknown): string {
  if (value == null) return '—'
  const str = String(value)
  const k = key.toLowerCase()
  if (
    k.includes('price') ||
    k === 'ema_fast' ||
    k === 'ema_slow' ||
    k === 'ema20' ||
    k === 'resistance' ||
    k === 'support'
  ) {
    return formatPrice(str)
  }
  if (k.includes('funding_rate')) return formatFunding(str)
  if (k.includes('volume_24h')) return formatVolume(str)
  if (k.includes('spread')) return formatSpread(str)
  if (k.endsWith('_pct') || k.includes('change_pct')) return formatPct(str)
  return str
}

export function contextFunding(context: Record<string, unknown> | undefined): string {
  if (!context?.funding_rate) return '—'
  return formatFunding(context.funding_rate as string | number)
}
