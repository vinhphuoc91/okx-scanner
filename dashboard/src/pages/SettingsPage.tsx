import { Minus, Plus, RotateCcw, Save, Settings2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  fetchStrategySettings,
  getApiErrorMessage,
  resetStrategySettings,
  updateGlobalSettings,
  updateStrategySettings,
} from '../api/client'
import { useToast } from '../components/Toast'
import type { GlobalSettings, StrategySettings, StrategySensitivity } from '../types/api'
import { gradeColor, gradeLabel } from '../utils/colors'

const STRATEGY_TABS = [
  { key: 'FUNDING', label: 'Funding' },
  { key: 'MOMENTUM', label: 'Momentum' },
  { key: 'BREAKOUT', label: 'Breakout' },
  { key: 'VOLUME_ANOMALY', label: 'Volume Anomaly' },
  { key: 'TREND_PULLBACK', label: 'Trend Pullback' },
  { key: 'CORRELATION_DIVERGENCE', label: 'Correlation Div.' },
  { key: 'LIQUIDATION_ZONE', label: 'Liquidation Zone' },
  { key: 'STAT_ARBITRAGE', label: 'Stat Arbitrage' },
] as const

const COOLDOWN_OPTIONS = [0.5, 1, 2, 4, 6, 8, 12, 24]
const REFRESH_OPTIONS = [5, 10, 15, 30, 60]
const SAMPLE_ATR = 500
const SAMPLE_PRICE = 67_000

function atrRiskReward(tpMult: number, slMult: number): number {
  if (slMult <= 0) return 0
  return tpMult / slMult
}

function breakevenWinRate(rr: number): number {
  if (rr <= 0) return 100
  return (1 / (1 + rr)) * 100
}

function Stepper({
  value,
  min,
  max,
  onChange,
}: {
  value: number
  min: number
  max: number
  onChange: (v: number) => void
}) {
  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        disabled={value <= min}
        onClick={() => onChange(Math.max(min, value - 1))}
        className="rounded border border-[#30363d] p-1 text-[#8b949e] hover:bg-[#21262d] disabled:opacity-40"
      >
        <Minus className="h-3.5 w-3.5" />
      </button>
      <span className="min-w-[2rem] text-center font-mono text-sm">{value}</span>
      <button
        type="button"
        disabled={value >= max}
        onClick={() => onChange(Math.min(max, value + 1))}
        className="rounded border border-[#30363d] p-1 text-[#8b949e] hover:bg-[#21262d] disabled:opacity-40"
      >
        <Plus className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 rounded-full transition-colors ${checked ? 'bg-[#388bfd]' : 'bg-[#30363d]'}`}
    >
      <span
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${checked ? 'left-5' : 'left-0.5'}`}
      />
    </button>
  )
}

export function SettingsPage() {
  const { show, Toast } = useToast()
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<string>('FUNDING')
  const [strategies, setStrategies] = useState<StrategySettings[]>([])
  const [global, setGlobal] = useState<GlobalSettings | null>(null)
  const [draft, setDraft] = useState<StrategySettings | null>(null)
  const [globalDraft, setGlobalDraft] = useState<GlobalSettings | null>(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await fetchStrategySettings()
      setStrategies(data.strategies)
      setGlobal(data.global)
      setGlobalDraft(data.global)
      const current = data.strategies.find((s) => s.strategy_type === activeTab) ?? data.strategies[0]
      if (current) {
        setDraft({ ...current })
        setActiveTab(current.strategy_type)
      }
    } catch (err) {
      show(getApiErrorMessage(err), 'error')
    } finally {
      setLoading(false)
    }
  }, [activeTab, show])

  useEffect(() => {
    void load()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const selectTab = (key: string) => {
    setActiveTab(key)
    const s = strategies.find((x) => x.strategy_type === key)
    if (s) setDraft({ ...s })
  }

  const saved = strategies.find((s) => s.strategy_type === activeTab)
  const hasUnsaved =
    draft !== null &&
    saved !== null &&
    JSON.stringify(draft) !== JSON.stringify(saved)

  const hasGlobalUnsaved =
    global !== null &&
    globalDraft !== null &&
    JSON.stringify(global) !== JSON.stringify(globalDraft)

  const previews = useMemo(() => {
    if (!draft) return []
    return [1, 2, 3].map((tier) => {
      const slMult = draft[`atr_sl_multiplier_t${tier}` as keyof StrategySettings] as number
      const tpMult = draft[`atr_tp_multiplier_t${tier}` as keyof StrategySettings] as number
      const slDist = SAMPLE_ATR * slMult
      const tpDist = SAMPLE_ATR * tpMult
      const slPct = (slDist / SAMPLE_PRICE) * 100
      const tpPct = (tpDist / SAMPLE_PRICE) * 100
      const rr = atrRiskReward(tpMult, slMult)
      return { tier, slMult, tpMult, slDist, tpDist, slPct, tpPct, rr, breakeven: breakevenWinRate(rr) }
    })
  }, [draft])

  const handleSave = async () => {
    if (!draft) return
    setSaving(true)
    try {
      const { strategy_type, updated_at: _, ...payload } = draft
      const updated = await updateStrategySettings(strategy_type, payload)
      setStrategies((prev) =>
        prev.map((s) => (s.strategy_type === updated.strategy_type ? updated : s)),
      )
      setDraft({ ...updated })
      show('Strategy settings saved')
    } catch (err) {
      show(getApiErrorMessage(err), 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveGlobal = async () => {
    if (!globalDraft) return
    setSaving(true)
    try {
      const { updated_at: _, ...payload } = globalDraft
      const updated = await updateGlobalSettings(payload)
      setGlobal(updated)
      setGlobalDraft({ ...updated })
      show('Global settings saved')
    } catch (err) {
      show(getApiErrorMessage(err), 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async () => {
    if (!confirm('Reset all strategies and global settings to defaults?')) return
    setSaving(true)
    try {
      const data = await resetStrategySettings()
      setStrategies(data.strategies)
      setGlobal(data.global)
      setGlobalDraft(data.global)
      const current = data.strategies.find((s) => s.strategy_type === activeTab) ?? data.strategies[0]
      if (current) setDraft({ ...current })
      show('Settings reset to defaults')
    } catch (err) {
      show(getApiErrorMessage(err), 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading || !draft || !globalDraft) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center p-6">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#388bfd] border-t-transparent" />
      </div>
    )
  }

  const grade = gradeLabel(null, draft.min_score)
  const gradeClr = gradeColor(null, draft.min_score)

  return (
    <div className="space-y-4 p-4 sm:p-6">
      {Toast}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Settings2 className="h-5 w-5 text-[#388bfd]" />
            <h1 className="text-lg font-semibold text-[#e6edf3]">Strategy Settings</h1>
          </div>
          <p className="mt-1 text-sm text-[#8b949e]">
            Configure risk profiles, TP/SL tiers, and scanner thresholds per strategy.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(hasUnsaved || hasGlobalUnsaved) && (
            <span className="self-center text-xs text-[#d29922]">Unsaved changes</span>
          )}
          <button
            type="button"
            onClick={() => void handleReset()}
            disabled={saving}
            className="flex items-center gap-1.5 rounded-lg border border-[#30363d] px-3 py-1.5 text-xs text-[#8b949e] hover:bg-[#21262d]"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Reset to Default
          </button>
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={saving || !hasUnsaved}
            className="flex items-center gap-1.5 rounded-lg bg-[#388bfd] px-3 py-1.5 text-xs font-medium text-white hover:bg-[#388bfd]/90 disabled:opacity-50"
          >
            <Save className="h-3.5 w-3.5" /> Save Changes
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-[#30363d] pb-1">
        {STRATEGY_TABS.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => selectTab(key)}
            className={`rounded-t-lg px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === key
                ? 'bg-[#161b22] text-[#388bfd] border border-b-0 border-[#30363d]'
                : 'text-[#8b949e] hover:text-[#e6edf3]'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
            <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-[#8b949e]">General</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#e6edf3]">Enable Strategy</span>
                <Toggle
                  checked={draft.is_enabled}
                  onChange={(v) => setDraft({ ...draft, is_enabled: v })}
                />
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm text-[#e6edf3]">Min Score</span>
                  <span
                    className="rounded px-2 py-0.5 font-mono text-xs font-bold"
                    style={{ color: gradeClr, backgroundColor: gradeClr + '22' }}
                  >
                    {draft.min_score} · {grade}
                  </span>
                </div>
                <input
                  type="range"
                  min={60}
                  max={95}
                  step={1}
                  value={draft.min_score}
                  onChange={(e) => setDraft({ ...draft, min_score: Number(e.target.value) })}
                  className="w-full accent-[#388bfd]"
                />
                <div className="mt-1 flex justify-between text-[10px] text-[#484f58]">
                  <span>60</span><span>95</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#e6edf3]">Max Concurrent Trades</span>
                <Stepper
                  value={draft.max_concurrent}
                  min={1}
                  max={10}
                  onChange={(v) => setDraft({ ...draft, max_concurrent: v })}
                />
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-[#e6edf3]">Cooldown</span>
                <select
                  value={draft.cooldown_hours}
                  onChange={(e) => setDraft({ ...draft, cooldown_hours: Number(e.target.value) })}
                  className="rounded-lg border border-[#30363d] bg-[#0d1117] px-2 py-1.5 text-sm text-[#e6edf3]"
                >
                  {COOLDOWN_OPTIONS.map((h) => (
                    <option key={h} value={h}>{h}h</option>
                  ))}
                </select>
              </div>
              <div>
                <span className="mb-2 block text-sm text-[#e6edf3]">Sensitivity</span>
                <div className="flex flex-wrap gap-2">
                  {(['LOW', 'MEDIUM', 'HIGH'] as StrategySensitivity[]).map((s) => (
                    <label key={s} className="flex cursor-pointer items-center gap-1.5 text-xs">
                      <input
                        type="radio"
                        name="sensitivity"
                        checked={draft.sensitivity === s}
                        onChange={() => setDraft({ ...draft, sensitivity: s })}
                        className="accent-[#388bfd]"
                      />
                      <span className={draft.sensitivity === s ? 'text-[#388bfd]' : 'text-[#8b949e]'}>{s}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#e6edf3]">Requires Confirmation</span>
                <Toggle
                  checked={draft.requires_confirmation}
                  onChange={(v) => setDraft({ ...draft, requires_confirmation: v })}
                />
              </div>
              {draft.requires_confirmation && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[#e6edf3]">Confirmation Candles (M15)</span>
                  <Stepper
                    value={draft.confirmation_candles}
                    min={1}
                    max={4}
                    onChange={(v) => setDraft({ ...draft, confirmation_candles: v })}
                  />
                </div>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-[#8b949e]">
              ATR Multipliers per Tier
            </h3>
            <p className="mb-4 text-xs text-[#484f58]">
              SL/TP distances = ATR × multiplier (absolute price, adapts per coin)
            </p>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[480px] text-sm">
                <thead>
                  <tr className="text-[10px] uppercase text-[#8b949e]">
                    <th className="pb-2 text-left" />
                    <th className="pb-2 text-center">Tier 1</th>
                    <th className="pb-2 text-center">Tier 2</th>
                    <th className="pb-2 text-center">Tier 3</th>
                  </tr>
                </thead>
                <tbody className="font-mono text-xs">
                  {(['atr_sl_multiplier', 'atr_tp_multiplier', 'timeout'] as const).map((row) => (
                    <tr key={row} className="border-t border-[#21262d]">
                      <td className="py-2 pr-4 text-[#8b949e] uppercase">
                        {row === 'timeout'
                          ? 'Timeout (h)'
                          : row === 'atr_sl_multiplier'
                            ? 'SL × ATR'
                            : 'TP × ATR'}
                      </td>
                      {[1, 2, 3].map((tier) => {
                        const field = `${row}_t${tier}` as keyof StrategySettings
                        return (
                          <td key={tier} className="py-2 text-center">
                            <input
                              type="number"
                              step={row === 'timeout' ? 1 : 0.1}
                              min={row === 'timeout' ? 1 : 0.1}
                              value={draft[field] as number}
                              onChange={(e) =>
                                setDraft({ ...draft, [field]: Number(e.target.value) })
                              }
                              className="w-16 rounded border border-[#30363d] bg-[#0d1117] px-1.5 py-1 text-center text-[#e6edf3]"
                            />
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-[#8b949e]">
              ATR Risk Preview
            </h3>
            <p className="mb-3 text-xs text-[#8b949e]">
              Sample: BTC @ ${SAMPLE_PRICE.toLocaleString()}, ATR = ${SAMPLE_ATR}
            </p>
            <ul className="space-y-3 text-sm">
              {previews.map(({ tier, slDist, tpDist, slPct, tpPct, rr, breakeven }) => (
                <li key={tier} className="rounded-lg bg-[#0d1117] p-3">
                  <p className="mb-1 text-[10px] uppercase text-[#8b949e]">Tier {tier}</p>
                  <p className="font-mono text-xs text-[#e6edf3]">
                    SL = ${slDist.toFixed(0)} ({slPct.toFixed(2)}%) · TP = ${tpDist.toFixed(0)} ({tpPct.toFixed(2)}%)
                  </p>
                  <p className="mt-1 text-[#e6edf3]">
                    R/R: <span className="font-mono font-bold text-[#388bfd]">{rr.toFixed(1)}</span>
                  </p>
                  <p className="text-xs text-[#8b949e]">
                    Breakeven win rate: <span className="font-mono text-[#d29922]">{breakeven.toFixed(1)}%</span>
                  </p>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-[#8b949e]">
              Global Settings
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#e6edf3]">Max Total Concurrent</span>
                <Stepper
                  value={globalDraft.max_total_concurrent_trades}
                  min={5}
                  max={50}
                  onChange={(v) => setGlobalDraft({ ...globalDraft, max_total_concurrent_trades: v })}
                />
              </div>
              <div>
                <div className="mb-2 flex justify-between text-sm">
                  <span className="text-[#e6edf3]">Alert Min Score</span>
                  <span className="font-mono text-[#388bfd]">{globalDraft.alert_min_score}</span>
                </div>
                <input
                  type="range"
                  min={50}
                  max={95}
                  value={globalDraft.alert_min_score}
                  onChange={(e) =>
                    setGlobalDraft({ ...globalDraft, alert_min_score: Number(e.target.value) })
                  }
                  className="w-full accent-[#388bfd]"
                />
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-[#e6edf3]">Auto-refresh</span>
                <select
                  value={globalDraft.auto_refresh_interval_seconds}
                  onChange={(e) =>
                    setGlobalDraft({
                      ...globalDraft,
                      auto_refresh_interval_seconds: Number(e.target.value),
                    })
                  }
                  className="rounded-lg border border-[#30363d] bg-[#0d1117] px-2 py-1.5 text-sm text-[#e6edf3]"
                >
                  {REFRESH_OPTIONS.map((s) => (
                    <option key={s} value={s}>{s}s</option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                onClick={() => void handleSaveGlobal()}
                disabled={saving || !hasGlobalUnsaved}
                className="w-full rounded-lg border border-[#388bfd]/40 bg-[#388bfd]/10 py-2 text-xs text-[#388bfd] hover:bg-[#388bfd]/20 disabled:opacity-50"
              >
                Save Global Settings
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
