import { useCallback, useEffect, useState } from 'react'
import { fetchOpportunities, getApiErrorMessage } from '../api/client'
import type { Opportunity } from '../types/api'

const REFRESH_MS = 10_000

export function useStrategyOpportunities(strategy?: string) {
  const [items, setItems] = useState<Opportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const res = await fetchOpportunities({
        strategy,
        limit: 200,
      })
      setItems(res.items)
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [strategy])

  useEffect(() => {
    void load()
    const id = setInterval(() => void load(), REFRESH_MS)
    return () => clearInterval(id)
  }, [load])

  return { items, loading, error, refresh: load }
}

export function useAllOpportunities() {
  return useStrategyOpportunities(undefined)
}
