import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, CheckCheck, ChevronsLeft, LogOut, Menu, Search, UserCircle2, X } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'
import { useBureaus } from '../../hooks/useData'
import { listOverlaps } from '../../api/intelligence'
import { listTransfers } from '../../api/cases'
import { listRelationships } from '../../api/relationships'
import { getUnreadCount, listNotifications, markAllRead, markRead } from '../../api/notifications'
import { cn } from '../../lib/cn'
import { ROLE_LABELS } from '../../lib/domain'
import { fromNow } from '../../lib/format'
import { Logo, LogoMark } from '../brand/Logo'
import { Avatar, BureauChip, LiveDot } from '../ui'
import { ToastContainer } from '../ToastContainer'
import { CommandPalette } from './CommandPalette'
import { NAV_ITEMS, type NavItem } from './nav'

const PRIORITY_DOT: Record<string, string> = {
  urgent: 'bg-rose-500', high: 'bg-orange-500', medium: 'bg-royal-500', low: 'bg-slate-400',
}

function useBadges(enabled: boolean) {
  const overlaps = useQuery({ queryKey: ['overlaps', 'badge'], queryFn: () => listOverlaps({ limit: 0 }), enabled, refetchInterval: 60000 })
  const transfers = useQuery({ queryKey: ['transfers', 'badge'], queryFn: () => listTransfers('requested'), enabled, refetchInterval: 60000 })
  const reviews = useQuery({ queryKey: ['relationships', 'badge'], queryFn: () => listRelationships({ review_status: 'pending', limit: 1 }), enabled, refetchInterval: 60000 })
  return {
    overlaps: overlaps.data ? overlaps.data.summary.critical + overlaps.data.summary.high : 0,
    overlapsCritical: (overlaps.data?.summary.critical ?? 0) > 0,
    transfers: transfers.data?.total ?? 0,
    reviews: reviews.data?.total ?? 0,
  }
}

function SidebarLink({ item, collapsed, badge, alarm, onNavigate }: { item: NavItem; collapsed: boolean; badge?: number; alarm?: boolean; onNavigate?: () => void }) {
  return (
    <NavLink
      to={item.to}
      end={item.to === '/cases'}
      onClick={onNavigate}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        cn(
          'group relative flex items-center gap-3 rounded-xl px-3 py-2 text-[13.5px] font-medium transition-all duration-200',
          isActive ? 'bg-white/[.08] text-white shadow-inset' : 'text-royal-100/60 hover:bg-white/[.04] hover:text-white',
          collapsed && 'justify-center px-0',
        )
      }
    >
      {({ isActive }) => (
        <>
          <span className={cn('absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-gold-400 transition-all duration-300', isActive ? 'opacity-100' : 'opacity-0')} />
          <item.icon className={cn('h-[18px] w-[18px] shrink-0 transition', isActive ? 'text-gold-300' : 'text-royal-200/50 group-hover:text-royal-100')} />
          {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
          {!!badge && (
            <span
              className={cn(
                'tabular rounded-full px-1.5 text-[10px] font-bold leading-[18px]',
                alarm ? 'bg-rose-500 text-white shadow-[0_0_12px_rgba(244,63,94,.6)]' : 'bg-white/10 text-royal-100',
                collapsed && 'absolute right-1.5 top-1',
              )}
            >
              {badge}
            </span>
          )}
        </>
      )}
    </NavLink>
  )
}

function NotificationsPopover() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const qc = useQueryClient()
  const navigate = useNavigate()
  const count = useQuery({ queryKey: ['notifications', 'count'], queryFn: getUnreadCount, refetchInterval: 30000 })
  const list = useQuery({ queryKey: ['notifications', 'latest'], queryFn: () => listNotifications({ limit: 8 }), enabled: open })
  const readAll = useMutation({ mutationFn: markAllRead, onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }) })
  useEffect(() => {
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false)
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])
  const n = count.data?.count ?? 0
  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={`Alerts (${n} unread)`}
        className="relative flex h-10 w-10 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
      >
        <Bell className="h-5 w-5" />
        {n > 0 && (
          <span className="absolute right-1.5 top-1.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-rose-500 px-1 text-[9px] font-bold text-white ring-2 ring-white">
            {n > 99 ? '99+' : n}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 top-12 z-50 w-[380px] animate-scale-in overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lift">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div>
              <p className="text-sm font-bold text-slate-900">Alerts</p>
              <p className="text-xs text-slate-500">{n} unread</p>
            </div>
            <button onClick={() => readAll.mutate()} className="inline-flex items-center gap-1 text-xs font-semibold text-royal-600 hover:text-royal-800">
              <CheckCheck className="h-3.5 w-3.5" /> Mark all read
            </button>
          </div>
          <div className="max-h-[420px] overflow-y-auto">
            {(list.data?.items ?? []).map((a) => (
              <button
                key={a.id}
                onClick={async () => {
                  if (!a.is_read) await markRead(a.id).catch(() => undefined)
                  qc.invalidateQueries({ queryKey: ['notifications'] })
                  setOpen(false)
                  navigate(a.link_url || '/notifications')
                }}
                className={cn('flex w-full gap-3 border-b border-slate-50 px-4 py-3 text-left transition hover:bg-slate-50', !a.is_read && 'bg-royal-50/40')}
              >
                <span className={cn('mt-1.5 h-2 w-2 shrink-0 rounded-full', PRIORITY_DOT[a.priority] ?? 'bg-slate-400', a.is_read && 'opacity-30')} />
                <span className="min-w-0">
                  <span className="block text-[13px] font-semibold text-slate-800">{a.title}</span>
                  <span className="mt-0.5 line-clamp-2 block text-xs text-slate-500">{a.message}</span>
                  <span className="mt-1 block text-[11px] text-slate-400">{fromNow(a.created_at)}</span>
                </span>
              </button>
            ))}
            {list.data && list.data.items.length === 0 && <p className="px-4 py-10 text-center text-sm text-slate-400">You are all caught up.</p>}
          </div>
          <Link to="/notifications" onClick={() => setOpen(false)} className="block bg-slate-50 py-2.5 text-center text-xs font-semibold text-slate-600 hover:text-slate-900">
            View all alerts
          </Link>
        </div>
      )}
    </div>
  )
}

export function AppLayout() {
  const { user, logout } = useAuth()
  const { byId } = useBureaus()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('ns_sidebar') === '1')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [palette, setPalette] = useState(false)
  const [userMenu, setUserMenu] = useState(false)
  const badges = useBadges(!!user)
  const bureau = user?.bureau_id ? byId.get(user.bureau_id) : undefined

  useEffect(() => {
    try { localStorage.setItem('ns_sidebar', collapsed ? '1' : '0') } catch { /* ignore */ }
  }, [collapsed])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPalette(true)
      }
      if (e.key === '/' && !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)) {
        e.preventDefault()
        setPalette(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    setMobileOpen(false)
    setUserMenu(false)
    window.scrollTo({ top: 0 })
  }, [location.pathname])

  const visible = NAV_ITEMS.filter((n) => !n.roles || (user && n.roles.includes(user.role as string)))
  const groups = Array.from(new Set(visible.map((n) => n.group)))
  const badgeFor = (n: NavItem) => (n.badge === 'overlaps' ? badges.overlaps : n.badge === 'transfers' ? badges.transfers : n.badge === 'reviews' ? badges.reviews : 0)

  const sidebar = (isMobile: boolean) => {
    const c = collapsed && !isMobile
    return (
      <div className="flex h-full flex-col bg-ink-900 bg-[radial-gradient(600px_300px_at_0%_0%,rgba(91,102,236,.18),transparent),radial-gradient(400px_300px_at_100%_100%,rgba(236,150,11,.08),transparent)]">
        <div className={cn('flex h-16 items-center border-b border-white/[.06] px-4', c ? 'justify-center' : 'justify-between')}>
          <Link to="/dashboard">{c ? <LogoMark size={34} /> : <Logo />}</Link>
          {isMobile && (
            <button onClick={() => setMobileOpen(false)} className="rounded-lg p-1.5 text-white/60 hover:bg-white/10" aria-label="Close menu">
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
        <nav className="dark-scroll flex-1 space-y-5 overflow-y-auto px-3 py-5">
          {groups.map((g) => (
            <div key={g}>
              {!c && <p className="mb-1.5 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-royal-200/35">{g}</p>}
              <div className="space-y-0.5">
                {visible.filter((n) => n.group === g).map((n) => (
                  <SidebarLink
                    key={n.to}
                    item={n}
                    collapsed={c}
                    badge={badgeFor(n)}
                    alarm={n.badge === 'overlaps' && badges.overlapsCritical}
                    onNavigate={() => setMobileOpen(false)}
                  />
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="border-t border-white/[.06] p-3">
          <div className={cn('flex items-center gap-3 rounded-xl bg-white/[.04] p-2.5', c && 'justify-center')}>
            <Avatar name={user?.full_name} size={34} className="ring-ink-900" />
            {!c && (
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-semibold text-white">{user?.full_name}</p>
                <p className="truncate text-[11px] text-royal-200/50">{bureau ? bureau.code : ROLE_LABELS[user?.role ?? ''] ?? user?.role}</p>
              </div>
            )}
            {!c && (
              <button onClick={logout} className="rounded-lg p-1.5 text-royal-200/50 transition hover:bg-white/10 hover:text-white" aria-label="Sign out" title="Sign out">
                <LogOut className="h-4 w-4" />
              </button>
            )}
          </div>
          {!isMobile && (
            <button
              onClick={() => setCollapsed((v) => !v)}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg py-1.5 text-[11px] font-medium text-royal-200/40 transition hover:text-royal-100"
            >
              <ChevronsLeft className={cn('h-4 w-4 transition-transform', c && 'rotate-180')} />
              {!c && 'Collapse'}
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-canvas">
      {/* Desktop sidebar */}
      <aside className={cn('fixed inset-y-0 left-0 z-40 hidden transition-[width] duration-300 lg:block', collapsed ? 'w-[76px]' : 'w-[264px]')}>
        {sidebar(false)}
      </aside>
      {/* Mobile sidebar */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 animate-fade-in bg-ink-950/60" onClick={() => setMobileOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-[280px] animate-slide-in-right [animation-direction:reverse]">{sidebar(true)}</aside>
        </div>
      )}

      <div className={cn('transition-[padding] duration-300', collapsed ? 'lg:pl-[76px]' : 'lg:pl-[264px]')}>
        {/* Top bar */}
        <header className="glass-light sticky top-0 z-30 border-b border-slate-200/70">
          <div className="mx-auto flex h-16 max-w-[1500px] items-center gap-3 px-4 sm:px-6">
            <button onClick={() => setMobileOpen(true)} className="rounded-xl p-2 text-slate-600 hover:bg-slate-100 lg:hidden" aria-label="Open menu">
              <Menu className="h-5 w-5" />
            </button>
            <button
              onClick={() => setPalette(true)}
              className="group flex h-10 min-w-0 flex-1 items-center gap-3 rounded-xl border border-slate-200 bg-white/80 px-3.5 text-left text-sm text-slate-400 shadow-[inset_0_1px_2px_rgba(16,24,64,.04)] transition hover:border-slate-300 sm:max-w-md"
            >
              <Search className="h-4 w-4 text-slate-400 group-hover:text-slate-600" />
              <span className="flex-1 truncate">Search cases, institutions, AICTE ID…</span>
              <span className="kbd hidden sm:inline-flex">Ctrl K</span>
            </button>
            <div className="ml-auto flex shrink-0 items-center gap-1.5">
              <span className="hidden items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[11px] font-semibold text-emerald-700 md:inline-flex">
                <LiveDot /> Live · all bureaus
              </span>
              {bureau && <BureauChip code={bureau.code} className="hidden md:inline-flex" />}
              <NotificationsPopover />
              <div className="relative">
                <button onClick={() => setUserMenu((v) => !v)} className="flex items-center gap-2 rounded-xl p-1 pr-2 transition hover:bg-slate-100" aria-label="Account">
                  <Avatar name={user?.full_name} size={32} />
                  <span className="hidden text-left leading-tight xl:block">
                    <span className="block text-[13px] font-semibold text-slate-800">{user?.full_name}</span>
                    <span className="block text-[11px] text-slate-500">{user?.designation ?? ROLE_LABELS[user?.role ?? '']}</span>
                  </span>
                </button>
                {userMenu && (
                  <div className="absolute right-0 top-12 z-50 w-60 animate-scale-in overflow-hidden rounded-2xl border border-slate-200 bg-white p-1.5 shadow-lift">
                    <div className="px-3 py-2.5">
                      <p className="text-sm font-semibold text-slate-900">{user?.full_name}</p>
                      <p className="truncate text-xs text-slate-500">{user?.email}</p>
                      <p className="mt-1.5 text-[11px] font-semibold text-royal-600">{ROLE_LABELS[user?.role ?? ''] ?? user?.role}</p>
                    </div>
                    <Link to="/profile" className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">
                      <UserCircle2 className="h-4 w-4" /> My profile
                    </Link>
                    <button onClick={logout} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-rose-600 hover:bg-rose-50">
                      <LogOut className="h-4 w-4" /> Sign out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:py-8">
          <div key={location.pathname} className="animate-fade-up">
            <Outlet />
          </div>
          <footer className="mt-12 flex flex-col items-center justify-between gap-2 border-t border-slate-200/70 pt-5 text-[11px] text-slate-400 sm:flex-row">
            <span>NYAYA SETU · Integrated Institution Complaint Monitoring · AICTE · SIH PS 26264</span>
            <span>Prototype · synthetic demo data · advisory intelligence, human decisions</span>
          </footer>
        </main>
      </div>

      <CommandPalette open={palette} onClose={() => setPalette(false)} />
      <ToastContainer />
    </div>
  )
}
