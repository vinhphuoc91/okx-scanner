export type TimeRangePreset = '1h' | '4h' | '12h' | 'today' | 'yesterday' | 'week' | 'custom'

export interface TimeRangeValue {
  preset: TimeRangePreset
  customFrom?: Date
  customTo?: Date
}

export const TIME_RANGE_PRESET_KEYS: { value: TimeRangePreset; labelKey: string }[] = [
  { value: '1h', labelKey: 'timeRange.1h' },
  { value: '4h', labelKey: 'timeRange.4h' },
  { value: '12h', labelKey: 'timeRange.12h' },
  { value: 'today', labelKey: 'timeRange.today' },
  { value: 'yesterday', labelKey: 'timeRange.yesterday' },
  { value: 'week', labelKey: 'timeRange.week' },
  { value: 'custom', labelKey: 'timeRange.custom' },
]

export const DEFAULT_TIME_RANGE: TimeRangeValue = { preset: 'today' }

export function formatShortDateTime(d: Date): string {
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${dd}/${mm} ${hh}:${min}`
}

export function toIsoParam(d: Date): string {
  return d.toISOString()
}

function startOfTodayLocal(): Date {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0)
}

function yesterdayRange(): { from: Date; to: Date } {
  const now = new Date()
  const from = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1, 0, 0, 0, 0)
  const to = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1, 23, 59, 59, 999)
  return { from, to }
}

function startOfWeekLocal(): Date {
  const now = new Date()
  const day = now.getDay()
  const daysSinceMonday = day === 0 ? 6 : day - 1
  return new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() - daysSinceMonday,
    0,
    0,
    0,
    0,
  )
}

export function resolveTimeRange(value: TimeRangeValue): { from: Date; to: Date } | null {
  const now = new Date()

  switch (value.preset) {
    case '1h':
      return { from: new Date(now.getTime() - 60 * 60 * 1000), to: now }
    case '4h':
      return { from: new Date(now.getTime() - 4 * 60 * 60 * 1000), to: now }
    case '12h':
      return { from: new Date(now.getTime() - 12 * 60 * 60 * 1000), to: now }
    case 'today':
      return { from: startOfTodayLocal(), to: now }
    case 'yesterday':
      return yesterdayRange()
    case 'week':
      return { from: startOfWeekLocal(), to: now }
    case 'custom':
      if (value.customFrom && value.customTo) {
        return { from: value.customFrom, to: value.customTo }
      }
      return null
    default:
      return null
  }
}

export function getTimeRangeLabel(
  value: TimeRangeValue,
  t: (key: string) => string,
): string {
  if (value.preset === 'custom' && value.customFrom && value.customTo) {
    return `${formatShortDateTime(value.customFrom)} → ${formatShortDateTime(value.customTo)}`
  }
  const preset = TIME_RANGE_PRESET_KEYS.find((p) => p.value === value.preset)
  return preset ? t(preset.labelKey) : t('timeRange.today')
}

export function isTimeRangeActive(value: TimeRangeValue): boolean {
  return value.preset !== 'today'
}

/** Convert Date to value for datetime-local input (local timezone). */
export function toDatetimeLocalValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function fromDatetimeLocalValue(value: string): Date | null {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

export function isWithinTimeRange(entryAt: string, range: { from: Date; to: Date }): boolean {
  const t = new Date(entryAt).getTime()
  return t >= range.from.getTime() && t <= range.to.getTime()
}
