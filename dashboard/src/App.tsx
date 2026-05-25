import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ErrorBoundary } from './components/ErrorBoundary'
import { Layout } from './components/layout/Layout'
import { DashboardPage } from './pages/DashboardPage'
import { AlertsPage } from './pages/AlertsPage'
import { FundingScannerPage } from './pages/FundingScannerPage'
import { MomentumScannerPage } from './pages/MomentumScannerPage'
import { BreakoutScannerPage } from './pages/BreakoutScannerPage'
import { VolumeAnomalyPage } from './pages/VolumeAnomalyPage'
import { TrendPullbackPage } from './pages/TrendPullbackPage'
import { CorrelationDivergencePage } from './pages/CorrelationDivergencePage'
import { LiquidationZonePage } from './pages/LiquidationZonePage'
import { StatArbitragePage } from './pages/StatArbitragePage'
import { MarketOverviewPage } from './pages/MarketOverviewPage'
import { SettingsPage } from './pages/SettingsPage'
import { PlaceholderPage } from './pages/PlaceholderPage'

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route
              path="opportunities"
              element={
                <PlaceholderPage
                  titleKey="placeholder.topOpportunities.title"
                  descriptionKey="placeholder.topOpportunities.desc"
                />
              }
            />
            <Route path="funding" element={<FundingScannerPage />} />
            <Route path="momentum" element={<MomentumScannerPage />} />
            <Route path="breakout" element={<BreakoutScannerPage />} />
            <Route path="volume-anomaly" element={<VolumeAnomalyPage />} />
            <Route path="trend-pullback" element={<TrendPullbackPage />} />
            <Route path="correlation-divergence" element={<CorrelationDivergencePage />} />
            <Route path="liquidation-zone" element={<LiquidationZonePage />} />
            <Route path="stat-arbitrage" element={<StatArbitragePage />} />
            <Route path="market" element={<MarketOverviewPage />} />
            <Route path="alerts" element={<AlertsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route
              path="logs"
              element={
                <PlaceholderPage
                  titleKey="placeholder.logs.title"
                  descriptionKey="placeholder.logs.desc"
                />
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
