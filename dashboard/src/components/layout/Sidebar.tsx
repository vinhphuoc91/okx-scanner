import { useCallback, useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  Activity,
  GitCompare,
  AlertTriangle,
  ArrowLeftRight,
  Bell,
  Bolt,
  ChartLine,
  ChevronsLeft,
  ChevronsRight,
  DollarSign,
  Globe,
  LayoutDashboard,
  LineChart,
  ListOrdered,
  Map,
  Settings,
  Terminal,
  TrendingUp,
  Trophy,
  Wallet,
  Zap,
} from 'lucide-react'
import { fetchAlertStats } from '../../api/client'
import { useTranslation } from '../../i18n/I18nProvider'

interface NavItem {
  labelKey: string
  path: string
  icon: React.ReactNode
  disabled?: boolean
}

interface NavSection {
  titleKey: string
  items: NavItem[]
}

const NAV_SECTIONS: NavSection[] = [
  {
    titleKey: 'nav.section.overview',
    items: [
      { labelKey: 'nav.dashboard', path: '/', icon: <LayoutDashboard className="h-4 w-4" /> },
      { labelKey: 'nav.marketOverview', path: '/market', icon: <Globe className="h-4 w-4" /> },
    ],
  },
  {
    titleKey: 'nav.section.scanners',
    items: [
      { labelKey: 'nav.fundingScanner', path: '/funding', icon: <DollarSign className="h-4 w-4" /> },
      { labelKey: 'nav.momentumScanner', path: '/momentum', icon: <TrendingUp className="h-4 w-4" /> },
      { labelKey: 'nav.breakoutScanner', path: '/breakout', icon: <Bolt className="h-4 w-4" /> },
      { labelKey: 'nav.volumeAnomaly', path: '/volume-anomaly', icon: <Activity className="h-4 w-4" /> },
      { labelKey: 'nav.trendPullback', path: '/trend-pullback', icon: <ChartLine className="h-4 w-4" /> },
      { labelKey: 'nav.correlationDivergence', path: '/correlation-divergence', icon: <GitCompare className="h-4 w-4" /> },
      { labelKey: 'nav.liquidationZone', path: '/liquidation-zone', icon: <AlertTriangle className="h-4 w-4" /> },
      { labelKey: 'nav.statArbitrage', path: '/stat-arbitrage', icon: <ArrowLeftRight className="h-4 w-4" /> },
    ],
  },
  {
    titleKey: 'nav.section.trading',
    items: [
      { labelKey: 'nav.topOpportunities', path: '/opportunities', icon: <Trophy className="h-4 w-4" /> },
      { labelKey: 'nav.alerts', path: '/alerts', icon: <Bell className="h-4 w-4" /> },
    ],
  },
  {
    titleKey: 'nav.section.system',
    items: [
      { labelKey: 'nav.settings', path: '/settings', icon: <Settings className="h-4 w-4" /> },
      { labelKey: 'nav.logs', path: '/logs', icon: <Terminal className="h-4 w-4" /> },
    ],
  },
]

const COMING_SOON_ITEMS: NavItem[] = [
  { labelKey: 'nav.pairTrading', path: '#', icon: <ArrowLeftRight className="h-4 w-4" />, disabled: true },
  { labelKey: 'nav.positions', path: '#', icon: <Wallet className="h-4 w-4" />, disabled: true },
  { labelKey: 'nav.orders', path: '#', icon: <ListOrdered className="h-4 w-4" />, disabled: true },
  { labelKey: 'nav.tradeHistory', path: '#', icon: <LineChart className="h-4 w-4" />, disabled: true },
  { labelKey: 'nav.performance', path: '#', icon: <Activity className="h-4 w-4" />, disabled: true },
  { labelKey: 'nav.liquidationMap', path: '#', icon: <Map className="h-4 w-4" />, disabled: true },
]

const COLLAPSED_KEY = 'okx-sidebar-collapsed'

function useRunningTradesBadge() {
  const [count, setCount] = useState(0)

  const load = useCallback(async () => {
    try {
      const stats = await fetchAlertStats()
      setCount(stats.running)
    } catch {
      /* keep last value */
    }
  }, [])

  useEffect(() => {
    void load()
    const id = setInterval(() => void load(), 30_000)
    return () => clearInterval(id)
  }, [load])

  return count
}

function navLinkClass(isActive: boolean, collapsed: boolean, disabled?: boolean) {
  if (disabled) {
    return `flex items-center rounded-lg py-2 text-sm text-[#484f58] opacity-35 cursor-not-allowed ${
      collapsed ? 'justify-center px-0' : 'gap-3 px-3'
    }`
  }

  const base = `flex items-center rounded-lg py-2 text-sm transition-all duration-200 ${
    collapsed ? 'justify-center px-0' : 'gap-3 px-3'
  }`

  if (isActive) {
    return `${base} border-l-2 border-[#388bfd] bg-[#1c2739] text-[#388bfd] ${
      collapsed ? 'pl-0' : 'pl-[10px]'
    }`
  }

  return `${base} border-l-2 border-transparent text-[#8b949e] hover:bg-[#161b22] hover:text-[#e6edf3] ${
    collapsed ? 'pl-0' : 'pl-[10px]'
  }`
}

function NavItemLink({
  item,
  collapsed,
  runningBadge,
  label,
}: {
  item: NavItem
  collapsed: boolean
  runningBadge?: number
  label: string
}) {
  const showBadge = item.path === '/alerts' && runningBadge != null && runningBadge > 0

  if (item.disabled) {
    return (
      <span title={collapsed ? label : undefined} className={navLinkClass(false, collapsed, true)}>
        <span className="relative shrink-0">{item.icon}</span>
        {!collapsed && label}
      </span>
    )
  }

  return (
    <NavLink
      to={item.path}
      end={item.path === '/'}
      title={collapsed ? label : undefined}
      className={({ isActive }) => navLinkClass(isActive, collapsed)}
    >
      <span className="relative shrink-0">
        {item.icon}
        {collapsed && showBadge && (
          <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-[#388bfd]" />
        )}
      </span>
      {!collapsed && (
        <>
          <span className="flex-1 truncate">{label}</span>
          {showBadge && (
            <span className="ml-auto rounded-full bg-[#388bfd]/20 px-1.5 py-0.5 font-mono text-[10px] font-bold text-[#388bfd]">
              {runningBadge > 99 ? '99+' : runningBadge}
            </span>
          )}
        </>
      )}
    </NavLink>
  )
}

function NavSectionBlock({
  section,
  collapsed,
  runningBadge,
  isFirst,
  t,
}: {
  section: NavSection
  collapsed: boolean
  runningBadge: number
  isFirst?: boolean
  t: (key: string) => string
}) {
  return (
    <div className={isFirst ? '' : 'mt-4'}>
      {!collapsed && (
        <p className="mb-2 px-3 text-xs uppercase tracking-wider text-[#484f58]">{t(section.titleKey)}</p>
      )}
      <ul className="space-y-0.5">
        {section.items.map((item) => (
          <li key={item.labelKey}>
            <NavItemLink
              item={item}
              collapsed={collapsed}
              runningBadge={item.path === '/alerts' ? runningBadge : undefined}
              label={t(item.labelKey)}
            />
          </li>
        ))}
      </ul>
    </div>
  )
}

export function Sidebar() {
  const { t } = useTranslation()
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(COLLAPSED_KEY) === 'true'
    } catch {
      return false
    }
  })
  const runningBadge = useRunningTradesBadge()

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem(COLLAPSED_KEY, String(next))
      } catch {
        /* ignore */
      }
      return next
    })
  }

  return (
    <aside
      className={`flex shrink-0 flex-col border-r border-[#30363d] bg-[#0d1117] transition-all duration-200 ${
        collapsed ? 'w-12' : 'w-56'
      }`}
    >
      <div className={`border-b border-[#30363d] transition-all duration-200 ${collapsed ? 'px-2 py-3' : 'px-4 py-4'}`}>
        <div className={`flex items-center ${collapsed ? 'justify-center' : 'gap-2'}`}>
          <div
            className={`flex shrink-0 items-center justify-center rounded-lg bg-[#388bfd]/20 transition-all duration-200 ${
              collapsed ? 'h-7 w-7' : 'h-8 w-8'
            }`}
            title={collapsed ? t('brand.title') : undefined}
          >
            <Zap className={`text-[#388bfd] transition-all duration-200 ${collapsed ? 'h-3.5 w-3.5' : 'h-4 w-4'}`} />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-[#e6edf3]">{t('brand.title')}</p>
              <p className="text-[10px] text-[#8b949e]">{t('brand.subtitle')}</p>
            </div>
          )}
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto overflow-x-hidden p-2">
        {NAV_SECTIONS.map((section, idx) => (
          <NavSectionBlock
            key={section.titleKey}
            section={section}
            collapsed={collapsed}
            runningBadge={runningBadge}
            isFirst={idx === 0}
            t={t}
          />
        ))}

        <div className="mt-4">
          {!collapsed && (
            <p className="mb-2 px-3 text-xs uppercase tracking-wider text-[#484f58]">{t('common.comingSoon')}</p>
          )}
          <ul className="space-y-0.5">
            {COMING_SOON_ITEMS.map((item) => (
              <li key={item.labelKey}>
                <NavItemLink item={item} collapsed={collapsed} label={t(item.labelKey)} />
              </li>
            ))}
          </ul>
        </div>
      </nav>

      <div className="border-t border-[#30363d] p-2">
        <button
          type="button"
          onClick={toggleCollapsed}
          title={collapsed ? t('common.expandSidebar') : t('common.collapseSidebar')}
          className={`flex w-full items-center rounded-lg py-2 text-[#8b949e] transition-all duration-200 hover:bg-[#161b22] hover:text-[#e6edf3] ${
            collapsed ? 'justify-center px-0' : 'justify-center px-3'
          }`}
        >
          {collapsed ? (
            <ChevronsRight className="h-4 w-4" />
          ) : (
            <ChevronsLeft className="h-4 w-4" />
          )}
        </button>
        {!collapsed && (
          <p className="mt-1 px-3 text-[10px] text-[#484f58]">{t('brand.version')}</p>
        )}
      </div>
    </aside>
  )
}
