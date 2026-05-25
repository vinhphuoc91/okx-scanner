import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  fetchAlerts,
  fetchAlertStats,
  fetchConfirmFailedAlerts,
  fetchOpportunities,
  fetchPendingAlerts,
  getApiErrorMessage,
} from '../api/client'
import type {
  AlertStatsResponse,
  Opportunity,
  PaperTrade,
  PendingAlertItem,
} from '../types/api'
import {
  resolveTimeRange,
  toIsoParam,
  type TimeRangeValue,
  isWithinTimeRange,
} from '../utils/timeRange'

const REFRESH_INTERVAL = 30_000

export interface AlertsFilters {
  status: string
  strategy: string
  tier: string
  direction: string
  timeRange: TimeRangeValue
  symbolSearch: string
}

export type StatusFilterKey =
  | 'all'
  | 'RUNNING'
  | 'WIN'
  | 'LOSS'
  | 'EXPIRED'
  | 'PENDING'
  | 'CONFIRM_FAILED'

function matchesStatusFilter(trade: PaperTrade, status: StatusFilterKey): boolean {
  if (status === 'all') return true
  if (status === 'PENDING') {
    return trade.status === 'PENDING' || trade.confirmation_status === 'PENDING'
  }
  if (status === 'CONFIRM_FAILED') {
    return trade.status === 'CONFIRM_FAILED' || trade.confirmation_status === 'FAILED'
  }
  return trade.status === status
}

function pendingToTrade(p: PendingAlertItem): PaperTrade {
  const entry = parseFloat(p.signal_price)
  const slDist = p.atr_value * p.sl_multiplier
  const tpDist = p.atr_value * p.tp_multiplier
  const isLong = p.direction === 'LONG'
  const slPrice = isLong ? entry - slDist : entry + slDist
  const tpPrice = isLong ? entry + tpDist : entry - tpDist
  const slPct = entry > 0 ? (Math.abs(slPrice - entry) / entry) * 100 : 0
  const tpPct = entry > 0 ? (Math.abs(tpPrice - entry) / entry) * 100 : 0

  return {
    id: -p.opportunity_id,
    opportunity_id: p.opportunity_id,
    symbol: p.symbol,
    strategy_type: p.strategy_type,
    direction: p.direction,
    entry_price: p.signal_price,
    tp_price: tpPrice.toFixed(8),
    sl_price: slPrice.toFixed(8),
    tp_pct: tpPct,
    sl_pct: slPct,
    timeout_hours: 0,
    status: 'PENDING',
    entry_at: p.entry_at,
    closed_at: null,
    close_price: null,
    pnl_pct: null,
    tier: p.tier,
    duration_seconds: null,
    atr_value: p.atr_value,
    sl_multiplier: p.sl_multiplier,
    tp_multiplier: p.tp_multiplier,
    signal_price: p.signal_price,
    confirmed_at: null,
    confirmation_required: true,
    confirmation_status: 'PENDING',
  }
}

function buildDateParams(timeRange: TimeRangeValue): Record<string, string> {
  const resolved = resolveTimeRange(timeRange)
  if (!resolved) return {}
  return {
    date_from: toIsoParam(resolved.from),
    date_to: toIsoParam(resolved.to),
  }
}

function applyFilters(
  items: PaperTrade[],
  filters: AlertsFilters,
  options?: { skipStatus?: boolean },
): PaperTrade[] {
  const range = resolveTimeRange(filters.timeRange)
  const query = filters.symbolSearch.trim().toLowerCase()

  return items.filter((t) => {
    if (!options?.skipStatus && !matchesStatusFilter(t, filters.status as StatusFilterKey)) {
      return false
    }

    if (filters.strategy !== 'all' && t.strategy_type !== filters.strategy) return false
    if (filters.tier !== 'all' && t.tier !== Number(filters.tier)) return false
    if (filters.direction !== 'all' && t.direction !== filters.direction) return false

    if (range !== null && !isWithinTimeRange(t.entry_at, range)) return false

    if (query && !t.symbol.toLowerCase().includes(query)) return false

    return true
  })
}

function buildStatusCounts(items: PaperTrade[]): Record<StatusFilterKey, number> {
  const keys: StatusFilterKey[] = [
    'all',
    'RUNNING',
    'WIN',
    'LOSS',
    'EXPIRED',
    'PENDING',
    'CONFIRM_FAILED',
  ]
  return Object.fromEntries(
    keys.map((key) => [key, items.filter((t) => matchesStatusFilter(t, key)).length]),
  ) as Record<StatusFilterKey, number>
}

export function useAlerts(filters: AlertsFilters) {
  const [rawItems, setRawItems] = useState<PaperTrade[]>([])
  const [opportunityMap, setOpportunityMap] = useState<Map<number, Opportunity>>(new Map())
  const [stats, setStats] = useState<AlertStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const dateParams = useMemo(() => buildDateParams(filters.timeRange), [filters.timeRange])

  const load = useCallback(async () => {
    setError(null)
    try {
      const params = { limit: 100, ...dateParams }

      const [tradesRes, statsRes, pendingRes, failedRes, oppRes] = await Promise.all([
        fetchAlerts(params),
        fetchAlertStats(dateParams),
        fetchPendingAlerts(),
        fetchConfirmFailedAlerts(params),
        fetchOpportunities({ limit: 100 }),
      ])

      const trades = tradesRes.items.map((t) => ({
        ...t,
        confirmation_status:
          t.confirmation_status ?? (t.confirmation_required ? 'CONFIRMED' : 'INSTANT'),
      }))

      const pendingIds = new Set(pendingRes.items.map((p) => p.opportunity_id))
      const withoutDupPending = trades.filter(
        (t) => !pendingIds.has(t.opportunity_id) || t.status !== 'RUNNING',
      )

      const merged = [
        ...pendingRes.items.map(pendingToTrade),
        ...failedRes.items,
        ...withoutDupPending,
      ]

      setRawItems(merged)
      setStats(statsRes)
      setOpportunityMap(new Map(oppRes.items.map((o) => [o.id, o])))
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [dateParams])

  const items = useMemo(() => applyFilters(rawItems, filters), [rawItems, filters])

  const statusCounts = useMemo(
    () => buildStatusCounts(applyFilters(rawItems, filters, { skipStatus: true })),
    [rawItems, filters],
  )

  useEffect(() => {
    void load()
    const id = setInterval(() => void load(), REFRESH_INTERVAL)
    return () => clearInterval(id)
  }, [load])

  return { items, stats, statusCounts, opportunityMap, loading, error, refresh: load }
}
