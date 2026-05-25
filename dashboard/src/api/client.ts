import axios from 'axios'
import type {
  AlertStatsResponse,
  AlertsResponse,
  GlobalSettings,
  HealthResponse,
  OpportunitiesResponse,
  PendingAlertItem,
  StatsResponse,
  StatusResponse,
  StrategySettings,
  StrategySettingsResponse,
} from '../types/api'

const api = axios.create({
  baseURL: '/api',
  timeout: 10_000,
  headers: { Accept: 'application/json' },
})

export async function fetchOpportunities(params?: {
  grade?: string
  strategy?: string
  limit?: number
}): Promise<OpportunitiesResponse> {
  const { data } = await api.get<OpportunitiesResponse>('/opportunities', { params })
  return data
}

export async function fetchStats(): Promise<StatsResponse> {
  const { data } = await api.get<StatsResponse>('/stats')
  return data
}

export async function fetchStatus(): Promise<StatusResponse> {
  const { data } = await api.get<StatusResponse>('/status')
  return data
}

export async function fetchAlerts(params?: Record<string, string | number>): Promise<AlertsResponse> {
  const { data } = await api.get<AlertsResponse>('/alerts', { params })
  return data
}

export async function fetchPendingAlerts(): Promise<{ count: number; items: PendingAlertItem[] }> {
  const { data } = await api.get<{ count: number; items: PendingAlertItem[] }>('/alerts/pending')
  return data
}

export async function fetchConfirmFailedAlerts(
  params?: Record<string, string | number>,
): Promise<AlertsResponse> {
  const { data } = await api.get<AlertsResponse>('/alerts/confirm-failed', { params })
  return data
}

export async function fetchAlertStats(
  params?: Record<string, string | number>,
): Promise<AlertStatsResponse> {
  const { data } = await api.get<AlertStatsResponse>('/alerts/stats', { params })
  return data
}

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>('/health')
  return data
}

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.code === 'ECONNABORTED') return 'Request timed out'
    if (!error.response) return 'Cannot reach API — is the server running on port 8000?'
    const detail = error.response.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg ?? '').join(', ')
    return `API error ${error.response.status}`
  }
  if (error instanceof Error) return error.message
  return 'Unknown error'
}

export async function fetchStrategySettings(): Promise<StrategySettingsResponse> {
  const { data } = await api.get<StrategySettingsResponse>('/settings/strategies')
  return data
}

export async function updateStrategySettings(
  strategyType: string,
  payload: Partial<Omit<StrategySettings, 'strategy_type' | 'updated_at'>>,
): Promise<StrategySettings> {
  const { data } = await api.put<StrategySettings>(`/settings/strategies/${strategyType}`, payload)
  return data
}

export async function resetStrategySettings(): Promise<StrategySettingsResponse> {
  const { data } = await api.post<StrategySettingsResponse>('/settings/strategies/reset')
  return data
}

export async function updateGlobalSettings(
  payload: Partial<Omit<GlobalSettings, 'updated_at'>>,
): Promise<GlobalSettings> {
  const { data } = await api.put<GlobalSettings>('/settings/global', payload)
  return data
}
