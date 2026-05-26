export interface AccountBalance {
  available: number
  total: number
}

export interface DailyRiskStatus {
  daily_loss_pct: number
  daily_loss_limit_pct: number
  remaining_pct: number
  is_blocked: boolean
}

export interface StrategyRealToggle {
  strategy_type: string
  real_trading_enabled: boolean
}

export async function fetchBalance(): Promise<AccountBalance> {
  const r = await fetch('/api/trading/balance')
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function fetchDailyRisk(): Promise<DailyRiskStatus> {
  const r = await fetch('/api/trading/daily-risk')
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function fetchStrategyToggles(): Promise<StrategyRealToggle[]> {
  const r = await fetch('/api/trading/strategy-toggles')
  if (!r.ok) throw new Error('Failed')
  return r.json()
}

export async function updateStrategyToggle(strategy: string, enabled: boolean): Promise<void> {
  await fetch(`/api/trading/strategy-toggles/${strategy}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ real_trading_enabled: enabled }),
  })
}
