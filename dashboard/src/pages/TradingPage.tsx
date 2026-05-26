import { useEffect, useState } from 'react'
import { Zap, ShieldAlert, Wallet, ToggleLeft, ToggleRight, ExternalLink } from 'lucide-react'
import { fetchTradingConfig, saveTradingConfig, type TradingConfig } from '../api/tradingConfig'
import { fetchBalance, fetchDailyRisk, fetchStrategyToggles, updateStrategyToggle,
  type AccountBalance, type DailyRiskStatus, type StrategyRealToggle } from '../api/trading'

const STRATEGY_LABELS: Record<string, string> = {
  FUNDING: '🔥 Funding',
  MOMENTUM: '📈 Momentum',
  BREAKOUT: '🚀 Breakout',
  VOLUME_ANOMALY: '📊 Vol Anomaly',
  TREND_PULLBACK: '📉 Trend Pullback',
  CORRELATION_DIVERGENCE: '🔗 Correlation Div.',
  LIQUIDATION_ZONE: '⚠️ Liquidation Zone',
  STAT_ARBITRAGE: '⚖️ Stat Arbitrage',
}

export function TradingPage() {
  const [cfg, setCfg] = useState<TradingConfig | null>(null)
  const [balance, setBalance] = useState<AccountBalance | null>(null)
  const [risk, setRisk] = useState<DailyRiskStatus | null>(null)
  const [toggles, setToggles] = useState<StrategyRealToggle[]>([])
  const [loading, setLoading] = useState(true)

  const isReal = cfg?.mode === 'real'

  useEffect(() => {
    Promise.all([
      fetchTradingConfig().then(setCfg),
      fetchStrategyToggles().then(setToggles),
    ]).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!isReal) return
    fetchBalance().then(setBalance)
    fetchDailyRisk().then(setRisk)
  }, [isReal])

  const handleModeToggle = async () => {
    if (!cfg) return
    const newMode = isReal ? 'paper' : 'real'
    if (newMode === 'real' && !window.confirm('Switch to REAL trading mode? The bot will place actual orders on OKX.')) return
    const updated = await saveTradingConfig({ mode: newMode })
    setCfg(updated)
  }

  const handleStrategyToggle = async (strategy: string, current: boolean) => {
    await updateStrategyToggle(strategy, !current)
    setToggles((prev) => prev.map((t) => t.strategy_type === strategy ? { ...t, real_trading_enabled: !current } : t))
  }

  if (loading) return <div className="flex h-64 items-center justify-center text-[#8b949e]">Loading...</div>

  return (
    <div className="space-y-5 p-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="h-5 w-5 text-[#d29922]" />
          <h1 className="text-lg font-semibold text-[#e6edf3]">Trading</h1>
        </div>
        <a href="/settings" className="flex items-center gap-1 text-xs text-[#8b949e] hover:text-[#e6edf3]">
          <ExternalLink className="h-3 w-3" /> API Settings
        </a>
      </div>

      {/* Mode toggle — big prominent card */}
      <div className={`rounded-xl border p-5 ${isReal ? 'border-[#f85149]/50 bg-[#f85149]/10' : 'border-[#30363d] bg-[#161b22]'}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase text-[#8b949e]">Trading Mode</p>
            <p className={`mt-1 text-2xl font-bold ${isReal ? 'text-[#f85149]' : 'text-[#388bfd]'}`}>
              {isReal ? '⚡ REAL' : '📋 PAPER'}
            </p>
            <p className="mt-1 text-xs text-[#8b949e]">
              {isReal ? 'Bot is placing actual orders on OKX' : 'Bot is simulating trades only'}
            </p>
          </div>
          <button type="button" onClick={handleModeToggle}
            className={`rounded-xl px-5 py-2.5 text-sm font-bold transition-colors ${
              isReal ? 'bg-[#f85149] text-white hover:bg-[#da3633]' : 'bg-[#238636] text-white hover:bg-[#2ea043]'
            }`}>
            {isReal ? 'Switch to Paper' : 'Go Live'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Account Balance */}
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
          <div className="mb-3 flex items-center gap-2">
            <Wallet className="h-4 w-4 text-[#3fb950]" />
            <h2 className="text-sm font-semibold text-[#e6edf3]">Account Balance</h2>
          </div>
          {isReal && balance ? (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-[#8b949e]">Available</span>
                <span className="font-mono font-bold text-[#3fb950]">${balance.available.toFixed(2)} USDT</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[#8b949e]">Total Equity</span>
                <span className="font-mono font-bold text-[#e6edf3]">${balance.total.toFixed(2)} USDT</span>
              </div>
              {cfg && (
                <div className="mt-3 grid grid-cols-3 gap-2 border-t border-[#30363d] pt-3">
                  {[1, 2, 3].map((t) => {
                    const pct = cfg[`size_pct_tier${t}` as keyof TradingConfig] as number
                    const sizeUsdt = (balance.available * pct / 100).toFixed(2)
                    return (
                      <div key={t} className="rounded-lg bg-[#0d1117] p-2 text-center">
                        <p className="text-[10px] text-[#8b949e]">T{t} size</p>
                        <p className="font-mono text-xs font-bold text-[#e6edf3]">${sizeUsdt}</p>
                        <p className="text-[10px] text-[#484f58]">{pct}%</p>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-[#484f58]">{isReal ? 'Loading balance...' : 'Available in Real mode'}</p>
          )}
        </div>

        {/* Daily Risk Status */}
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
          <div className="mb-3 flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-[#d29922]" />
            <h2 className="text-sm font-semibold text-[#e6edf3]">Daily Risk</h2>
          </div>
          {isReal && risk ? (
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-[#8b949e]">Today's Loss</span>
                <span className={`font-mono font-bold ${risk.daily_loss_pct > 0 ? 'text-[#f85149]' : 'text-[#3fb950]'}`}>
                  -{risk.daily_loss_pct.toFixed(2)}%
                </span>
              </div>
              <div>
                <div className="mb-1 flex justify-between text-[10px] text-[#8b949e]">
                  <span>Limit: {risk.daily_loss_limit_pct}%</span>
                  <span>Remaining: {risk.remaining_pct.toFixed(2)}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-[#21262d]">
                  <div className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(100, (risk.daily_loss_pct / risk.daily_loss_limit_pct) * 100)}%`,
                      backgroundColor: risk.is_blocked ? '#f85149' : '#d29922',
                    }} />
                </div>
              </div>
              {risk.is_blocked && (
                <p className="rounded-lg bg-[#f85149]/10 px-3 py-2 text-xs font-bold text-[#f85149]">
                  ⛔ Trading halted — daily loss limit reached
                </p>
              )}
            </div>
          ) : (
            <p className="text-sm text-[#484f58]">{isReal ? 'Loading...' : 'Available in Real mode'}</p>
          )}
        </div>
      </div>

      {/* Strategy toggles */}
      <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
        <h2 className="mb-3 text-sm font-semibold text-[#e6edf3]">Strategy Real Trading</h2>
        <p className="mb-4 text-xs text-[#8b949e]">Enable real orders per strategy. Only applies when mode is REAL.</p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {toggles.map((t) => (
            <button key={t.strategy_type} type="button"
              onClick={() => handleStrategyToggle(t.strategy_type, t.real_trading_enabled)}
              className={`flex items-center justify-between rounded-lg border px-3 py-2.5 text-left transition-colors ${
                t.real_trading_enabled
                  ? 'border-[#3fb950]/50 bg-[#3fb950]/10'
                  : 'border-[#30363d] bg-[#0d1117]'
              }`}>
              <span className="text-xs font-medium text-[#e6edf3]">
                {STRATEGY_LABELS[t.strategy_type] ?? t.strategy_type}
              </span>
              {t.real_trading_enabled
                ? <ToggleRight className="h-4 w-4 shrink-0 text-[#3fb950]" />
                : <ToggleLeft className="h-4 w-4 shrink-0 text-[#484f58]" />}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
