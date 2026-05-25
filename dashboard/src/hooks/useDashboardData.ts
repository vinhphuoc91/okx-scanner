import { useCallback, useEffect, useRef, useState } from 'react'
import {
  fetchHealth,
  fetchOpportunities,
  fetchStats,
  fetchStatus,
  getApiErrorMessage,
} from '../api/client'
import type {
  HealthResponse,
  Opportunity,
  StatsResponse,
  StatusResponse,
} from '../types/api'

const REFRESH_INTERVAL = 10

export interface DashboardData {
  opportunities: Opportunity[]
  stats: StatsResponse | null
  status: StatusResponse | null
  health: HealthResponse | null
  loading: boolean
  error: string | null
  countdown: number
  lastUpdated: Date | null
  refresh: () => void
}

export function useDashboardData(): DashboardData {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [countdown, setCountdown] = useState(REFRESH_INTERVAL)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const fetching = useRef(false)

  const load = useCallback(async () => {
    if (fetching.current) return
    fetching.current = true
    setError(null)

    try {
      const [oppRes, statsRes, statusRes, healthRes] = await Promise.all([
        fetchOpportunities({ limit: 100 }),
        fetchStats(),
        fetchStatus(),
        fetchHealth(),
      ])
      setOpportunities(oppRes.items)
      setStats(statsRes)
      setStatus(statusRes)
      setHealth(healthRes)
      setLastUpdated(new Date())
      setCountdown(REFRESH_INTERVAL)
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setLoading(false)
      fetching.current = false
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    const tick = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          void load()
          return REFRESH_INTERVAL
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(tick)
  }, [load])

  return {
    opportunities,
    stats,
    status,
    health,
    loading,
    error,
    countdown,
    lastUpdated,
    refresh: load,
  }
}
