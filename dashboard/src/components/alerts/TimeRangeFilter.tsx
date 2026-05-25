import { useEffect, useState } from 'react'
import { useTranslation } from '../../i18n/I18nProvider'
import {
  DEFAULT_TIME_RANGE,
  TIME_RANGE_PRESET_KEYS,
  formatShortDateTime,
  fromDatetimeLocalValue,
  getTimeRangeLabel,
  isTimeRangeActive,
  toDatetimeLocalValue,
  type TimeRangePreset,
  type TimeRangeValue,
} from '../../utils/timeRange'

interface TimeRangeFilterProps {
  value: TimeRangeValue
  onChange: (value: TimeRangeValue) => void
}

export function TimeRangeFilter({ value, onChange }: TimeRangeFilterProps) {
  const { t } = useTranslation()
  const [draftFrom, setDraftFrom] = useState('')
  const [draftTo, setDraftTo] = useState('')
  const active = isTimeRangeActive(value)

  useEffect(() => {
    if (value.preset === 'custom' && value.customFrom && value.customTo) {
      setDraftFrom(toDatetimeLocalValue(value.customFrom))
      setDraftTo(toDatetimeLocalValue(value.customTo))
    }
  }, [value.customFrom, value.customTo, value.preset])

  const handlePresetChange = (preset: TimeRangePreset) => {
    if (preset === 'custom') {
      const now = new Date()
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0)
      setDraftFrom(toDatetimeLocalValue(start))
      setDraftTo(toDatetimeLocalValue(now))
      onChange({ preset: 'custom' })
      return
    }
    onChange({ preset })
  }

  const handleApply = () => {
    const from = fromDatetimeLocalValue(draftFrom)
    const to = fromDatetimeLocalValue(draftTo)
    if (!from || !to || from > to) return
    onChange({ preset: 'custom', customFrom: from, customTo: to })
  }

  const handleClear = () => {
    setDraftFrom('')
    setDraftTo('')
    onChange(DEFAULT_TIME_RANGE)
  }

  const selectLabel = getTimeRangeLabel(value, t)

  return (
    <div className="relative flex flex-col gap-2">
      <select
        value={value.preset}
        onChange={(e) => handlePresetChange(e.target.value as TimeRangePreset)}
        title={selectLabel}
        className={`max-w-[220px] truncate rounded-md border px-3 py-1.5 text-xs ${
          active
            ? 'border-[#388bfd] bg-[#388bfd]/15 text-[#388bfd]'
            : 'border-[#30363d] bg-[#21262d] text-[#e6edf3]'
        }`}
      >
        {TIME_RANGE_PRESET_KEYS.map((p) => (
          <option key={p.value} value={p.value}>
            {p.value === 'custom' && value.customFrom && value.customTo
              ? selectLabel
              : t(p.labelKey)}
          </option>
        ))}
      </select>

      {value.preset === 'custom' && (
        <div className="flex flex-wrap items-end gap-2 rounded-md border border-[#30363d] bg-[#161b22] p-3">
          <label className="flex flex-col gap-1 text-[10px] text-[#8b949e]">
            {t('common.from')}
            <input
              type="datetime-local"
              value={draftFrom}
              onChange={(e) => setDraftFrom(e.target.value)}
              className="rounded-md border border-[#30363d] bg-[#21262d] px-2 py-1.5 text-xs text-[#e6edf3]"
            />
          </label>
          <label className="flex flex-col gap-1 text-[10px] text-[#8b949e]">
            {t('common.to')}
            <input
              type="datetime-local"
              value={draftTo}
              onChange={(e) => setDraftTo(e.target.value)}
              className="rounded-md border border-[#30363d] bg-[#21262d] px-2 py-1.5 text-xs text-[#e6edf3]"
            />
          </label>
          <button
            type="button"
            onClick={handleApply}
            className="rounded-md bg-[#388bfd] px-3 py-1.5 text-xs font-medium text-white hover:bg-[#4493ff]"
          >
            {t('common.apply')}
          </button>
          <button
            type="button"
            onClick={handleClear}
            className="rounded-md border border-[#30363d] px-3 py-1.5 text-xs text-[#8b949e] hover:text-[#e6edf3]"
          >
            {t('common.clear')}
          </button>
          {value.customFrom && value.customTo && (
            <span className="w-full text-[10px] text-[#388bfd]">
              {formatShortDateTime(value.customFrom)} → {formatShortDateTime(value.customTo)}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
