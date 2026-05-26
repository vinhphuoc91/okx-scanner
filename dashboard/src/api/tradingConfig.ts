const BASE = '/api/trading'

export interface TradingConfig {
  mode: 'paper' | 'real'
  api_key: string | null
  api_secret: string | null
  api_passphrase: string | null
  daily_loss_limit_pct: number
  size_pct_tier1: number
  size_pct_tier2: number
  size_pct_tier3: number
  max_leverage: number
  updated_at: string
}

export async function fetchTradingConfig(): Promise<TradingConfig> {
  const r = await fetch(`${BASE}/config`)
  if (!r.ok) throw new Error('Failed to fetch trading config')
  return r.json()
}

export async function saveTradingConfig(data: Partial<TradingConfig>): Promise<TradingConfig> {
  const r = await fetch(`${BASE}/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error('Failed to save trading config')
  return r.json()
}

export async function testConnection(): Promise<{ success: boolean; message: string }> {
  const r = await fetch(`${BASE}/test-connection`, { method: 'POST' })
  return r.json()
}
