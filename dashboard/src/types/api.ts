export interface OpportunityScores {
  trend: number | null
  momentum: number | null
  volume: number | null
  spread: number | null
  liquidity: number | null
  funding: number | null
  risk_penalty: number | null
}

export interface Opportunity {
  id: number
  symbol: string
  tier: number | null
  strategy: string
  direction: 'LONG' | 'SHORT'
  status: string
  total_score: number
  grade: string | null
  detected_at: string
  context?: Record<string, unknown>
  scores: OpportunityScores
}

export interface AlertItem {
  id: number
  alert_id: number | null
  time: string
  symbol: string
  tier: number | null
  strategy: string
  direction: 'LONG' | 'SHORT'
  total_score: number
  grade: string | null
  channel: string | null
  status: string
  scores: OpportunityScores
}

export interface PaperTrade {
  id: number
  opportunity_id: number
  symbol: string
  strategy_type: string
  direction: 'LONG' | 'SHORT'
  entry_price: string
  tp_price: string
  sl_price: string
  tp_pct: number
  sl_pct: number
  timeout_hours: number
  status: 'RUNNING' | 'WIN' | 'LOSS' | 'EXPIRED' | 'CANCELLED' | 'PENDING' | 'CONFIRM_FAILED'
  entry_at: string
  closed_at: string | null
  close_price: string | null
  pnl_pct: number | null
  tier: number
  duration_seconds: number | null
  atr_value: number | null
  sl_multiplier: number | null
  tp_multiplier: number | null
  signal_price: string | null
  confirmed_at: string | null
  confirmation_required: boolean
  confirmation_status: 'INSTANT' | 'CONFIRMED' | 'PENDING' | 'FAILED'
  total_score?: number | null
  grade?: string | null
}

export interface PendingAlertItem {
  opportunity_id: number
  symbol: string
  strategy_type: string
  direction: 'LONG' | 'SHORT'
  tier: number
  signal_price: string
  atr_value: number
  sl_multiplier: number
  tp_multiplier: number
  status: 'PENDING'
  confirmation_status: 'PENDING'
  entry_at: string
  created_at: string
}

export interface StrategyStats {
  count: number
  closed: number
  wins: number
  running?: number
  win_rate: number
  avg_pnl: number
}

export interface AlertStatsResponse {
  total_trades: number
  running: number
  wins: number
  losses: number
  expired: number
  win_rate: number
  avg_pnl: number
  by_strategy: Record<string, StrategyStats>
  by_tier: Record<string, StrategyStats>
  best_trade: PaperTrade | null
  worst_trade: PaperTrade | null
  pnl_by_day: { date: string; daily_pnl: number; cumulative_pnl: number }[]
  confirmation_rate: number
  avg_confirm_minutes: number
  confirm_failed_rate: number
  pending_confirmations: number
  instant_trades: number
  confirmed_trades: number
  confirm_failed_count: number
}

export interface AlertsResponse {
  count: number
  items: PaperTrade[]
}

export interface OpportunitiesResponse {
  count: number
  items: Opportunity[]
}

export interface StatsResponse {
  total_today: number
  by_grade: {
    excellent: number
    good: number
    watch: number
  }
  by_strategy: {
    funding: number
    momentum: number
  }
  top_opportunities: Opportunity[]
}

export interface StatusResponse {
  scanner_running: boolean
  started_at: string | null
  heartbeat_at: string | null
  uptime_seconds: number | null
  last_scan_by_tier: Record<string, string | null>
  worker_totals: Record<string, number>
}

export interface ComponentCheck {
  status: 'ok' | 'degraded' | 'down'
  latency_ms: number
  detail?: string | null
}

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'down'
  service: string
  version: string
  env: string
  checks: {
    database: ComponentCheck
    redis: ComponentCheck
    scanner: ComponentCheck
  }
  scanner: {
    running?: boolean
    heartbeat_at?: string | null
    uptime_seconds?: string | null
  }
}

export type GradeFilter = 'all' | 'excellent' | 'good' | 'watch'
export type StrategyFilter = 'all' | 'FUNDING' | 'MOMENTUM'

export type StrategySensitivity = 'LOW' | 'MEDIUM' | 'HIGH'

export interface StrategySettings {
  strategy_type: string
  is_enabled: boolean
  min_score: number
  max_concurrent: number
  cooldown_hours: number
  sensitivity: StrategySensitivity
  tp_tier1: number
  tp_tier2: number
  tp_tier3: number
  sl_tier1: number
  sl_tier2: number
  sl_tier3: number
  timeout_tier1: number
  timeout_tier2: number
  timeout_tier3: number
  requires_confirmation: boolean
  confirmation_candles: number
  atr_sl_multiplier_t1: number
  atr_sl_multiplier_t2: number
  atr_sl_multiplier_t3: number
  atr_tp_multiplier_t1: number
  atr_tp_multiplier_t2: number
  atr_tp_multiplier_t3: number
  updated_at: string
}

export interface GlobalSettings {
  max_total_concurrent_trades: number
  alert_min_score: number
  auto_refresh_interval_seconds: number
  updated_at: string
}

export interface StrategySettingsResponse {
  strategies: StrategySettings[]
  global: GlobalSettings
}
