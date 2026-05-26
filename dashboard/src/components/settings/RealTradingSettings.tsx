import { useState, useEffect } from 'react'
import { fetchTradingConfig, saveTradingConfig, testConnection, type TradingConfig } from '../../api/tradingConfig'

export function RealTradingSettings() {
  const [cfg, setCfg] = useState<TradingConfig | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [apiPass, setApiPass] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => { fetchTradingConfig().then(setCfg) }, [])

  if (!cfg) return <div className="text-xs text-[#8b949e]">Loading...</div>

  const handleSave = async () => {
    setSaving(true)
    const updates: Partial<TradingConfig> = {
      daily_loss_limit_pct: cfg.daily_loss_limit_pct,
      size_pct_tier1: cfg.size_pct_tier1,
      size_pct_tier2: cfg.size_pct_tier2,
      size_pct_tier3: cfg.size_pct_tier3,
      max_leverage: cfg.max_leverage,
    }
    if (apiKey) updates.api_key = apiKey
    if (apiSecret) updates.api_secret = apiSecret
    if (apiPass) updates.api_passphrase = apiPass
    const updated = await saveTradingConfig(updates)
    setCfg(updated)
    setApiKey(''); setApiSecret(''); setApiPass('')
    setSaving(false); setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleModeToggle = async (mode: 'paper' | 'real') => {
    const updated = await saveTradingConfig({ mode })
    setCfg(updated)
  }

  const handleTest = async () => {
    setTesting(true); setTestResult(null)
    const result = await testConnection()
    setTestResult(result); setTesting(false)
  }

  return (
    <div className="space-y-5">
      {/* Mode toggle */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase text-[#8b949e]">Trading Mode</p>
        <div className="flex gap-2">
          {(['paper', 'real'] as const).map((m) => (
            <button key={m} type="button" onClick={() => handleModeToggle(m)}
              className={`rounded-lg px-4 py-2 text-sm font-bold transition-colors ${
                cfg.mode === m
                  ? m === 'real' ? 'bg-[#f85149] text-white' : 'bg-[#388bfd] text-white'
                  : 'border border-[#30363d] text-[#8b949e] hover:text-[#e6edf3]'
              }`}>
              {m === 'paper' ? '📋 Paper Trading' : '⚡ Real Trading'}
            </button>
          ))}
        </div>
        {cfg.mode === 'real' && (
          <p className="mt-2 text-xs text-[#f85149]">⚠️ Real mode active — bot will place actual orders on OKX.</p>
        )}
      </div>

      {/* API Keys */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase text-[#8b949e]">OKX API Credentials</p>
        <div className="space-y-2">
          {[
            { label: 'API Key', value: apiKey, set: setApiKey, placeholder: cfg.api_key ? '••••••••' : 'Enter API Key' },
            { label: 'API Secret', value: apiSecret, set: setApiSecret, placeholder: cfg.api_secret ? '••••••••' : 'Enter API Secret' },
            { label: 'Passphrase', value: apiPass, set: setApiPass, placeholder: cfg.api_passphrase ? '••••••••' : 'Enter Passphrase' },
          ].map((f) => (
            <div key={f.label}>
              <label className="mb-1 block text-[10px] text-[#8b949e]">{f.label}</label>
              <input type="password" value={f.value} onChange={(e) => f.set(e.target.value)}
                placeholder={f.placeholder}
                className="w-full rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2 font-mono text-xs text-[#e6edf3] focus:border-[#388bfd] focus:outline-none" />
            </div>
          ))}
        </div>
        <div className="mt-2 flex gap-2">
          <button type="button" onClick={handleTest} disabled={testing}
            className="rounded-lg border border-[#30363d] px-3 py-1.5 text-xs text-[#8b949e] hover:text-[#e6edf3] disabled:opacity-50">
            {testing ? 'Testing...' : 'Test Connection'}
          </button>
          {testResult && (
            <span className={`text-xs ${testResult.success ? 'text-[#3fb950]' : 'text-[#f85149]'}`}>
              {testResult.success ? '✓' : '✗'} {testResult.message}
            </span>
          )}
        </div>
      </div>

      {/* Risk params */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase text-[#8b949e]">Risk Controls</p>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Daily Loss Limit (%)', key: 'daily_loss_limit_pct' as const },
            { label: 'Max Leverage', key: 'max_leverage' as const },
            { label: 'Size Tier 1 (% balance)', key: 'size_pct_tier1' as const },
            { label: 'Size Tier 2 (% balance)', key: 'size_pct_tier2' as const },
            { label: 'Size Tier 3 (% balance)', key: 'size_pct_tier3' as const },
          ].map((f) => (
            <div key={f.key}>
              <label className="mb-1 block text-[10px] text-[#8b949e]">{f.label}</label>
              <input type="number" value={cfg[f.key]} step="0.1" min="0"
                onChange={(e) => setCfg({ ...cfg, [f.key]: parseFloat(e.target.value) })}
                className="w-full rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2 font-mono text-xs text-[#e6edf3] focus:border-[#388bfd] focus:outline-none" />
            </div>
          ))}
        </div>
      </div>

      <button type="button" onClick={handleSave} disabled={saving}
        className="rounded-lg bg-[#238636] px-4 py-2 text-sm font-bold text-white hover:bg-[#2ea043] disabled:opacity-50">
        {saving ? 'Saving...' : saved ? '✓ Saved' : 'Save Settings'}
      </button>
    </div>
  )
}
