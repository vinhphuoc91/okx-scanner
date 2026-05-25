import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { useDashboardData } from '../../hooks/useDashboardData'
import { ApiErrorBanner } from '../ApiErrorBanner'

export function Layout() {
  const data = useDashboardData()

  return (
    <div className="flex h-screen overflow-hidden bg-[#0d1117]">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          opportunities={data.opportunities}
          stats={data.stats}
          status={data.status}
          countdown={data.countdown}
          loading={data.loading}
          onRefresh={data.refresh}
        />
        {data.error && <ApiErrorBanner message={data.error} onRetry={data.refresh} />}
        <main className="flex-1 overflow-y-auto">
          <Outlet context={data} />
        </main>
      </div>
    </div>
  )
}
