import { useEffect, useState } from 'react'
import { Avatar } from '@/components/Avatar'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { ChatWidget } from '@/features/chat/ChatWidget'
import { TripSearch } from '@/components/TripSearch'
import { Icon, LogoMark, type IconName } from '@/components/Icon'

/** One page width for the whole app: full-bleed up to 1440px, with side
 *  padding that grows from phone to laptop. */
export const CONTAINER = 'mx-auto w-full max-w-[1440px] px-4 sm:px-6 lg:px-10'

const FULL_BLEED = ['/', '/login', '/signup', '/signup/business', '/forgot-password', '/reset-password']

export function AppShell() {
  const location = useLocation()
  // The admin area is its own place: its own door (/admin/login), its own
  // header, and no traveller chrome -- no trip links, no support widget.
  const inAdmin = location.pathname === '/admin' || location.pathname.startsWith('/admin/')

  return (
    <div className="flex min-h-dvh flex-col overflow-x-clip bg-slate-50 text-slate-900 antialiased">
      {inAdmin ? <AdminHeader /> : <SiteHeader />}

      {FULL_BLEED.includes(location.pathname) ? (
        <div className="flex-1">
          <Outlet />
        </div>
      ) : (
        <main className={`${CONTAINER} flex-1 pt-6 pb-24 sm:pt-8`}>
          <Outlet />
        </main>
      )}

      <TravellerChat inAdmin={inAdmin} />
    </div>
  )
}

function SiteHeader() {
  const { user, isAuthenticated, isAdmin, isBusiness, logout } = useAuth()
  const { pathname } = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  // Close the phone menu whenever the page changes.
  useEffect(() => setMenuOpen(false), [pathname])

  const navCls = (to: string) =>
    `rounded-lg px-3 py-2 text-sm transition hover:bg-slate-100 ${
      pathname.startsWith(to) ? 'font-medium text-slate-950' : 'text-slate-600'
    }`

  const links: { to: string; label: string; icon: IconName; show: boolean }[] = [
    { to: '/business', label: 'Partner dashboard', icon: 'landmark', show: isBusiness },
    { to: '/dashboard', label: 'My trips', icon: 'dashboard', show: isAuthenticated && !isBusiness },
    { to: '/assistant', label: 'Assistant', icon: 'compass', show: isAuthenticated && !isBusiness },
    { to: '/recommend', label: 'Where to go', icon: 'wallet', show: isAuthenticated && !isBusiness },
    { to: '/packages', label: 'Packages', icon: 'bag', show: true },
    { to: '/book', label: 'Book travel', icon: 'train', show: isAuthenticated && !isBusiness && !isAdmin },
    { to: '/insights', label: 'Insights', icon: 'chart', show: true },
    { to: '/admin', label: 'Admin', icon: 'shield', show: isAdmin },
  ]

  return (
    <header className="sticky top-0 z-[1200] border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <nav className={`${CONTAINER} flex h-16 items-center justify-between gap-4`}>
        {/* Logged in: the logo goes to your trips; logged out: to the landing page. */}
        <Link
          to={isAdmin ? '/admin' : isBusiness ? '/business' : isAuthenticated ? '/dashboard' : '/'}
          className="flex shrink-0 items-center gap-2.5 whitespace-nowrap text-base font-semibold tracking-tight"
        >
          <LogoMark className="h-9 w-auto" />
          <span className="hidden min-[360px]:inline">Safarnama</span>
        </Link>

        {/* ---- laptop / tablet ---- */}
        <div className="hidden flex-1 items-center justify-end gap-2 md:flex lg:gap-3">
          {isAuthenticated && (
            <div className="mr-auto ml-6 max-w-md flex-1 lg:ml-10">
              <TripSearch />
            </div>
          )}
          {links
            .filter((l) => l.show && (isAuthenticated ? l.to !== '/insights' : true))
            .map((l) => (
              <Link key={l.to} to={l.to} className={navCls(l.to)}>
                {l.label}
              </Link>
            ))}
          {isAuthenticated ? (
            <>
              <Link
                to="/profile"
                title="Your profile"
                className={`ml-1 rounded-full ring-offset-2 transition hover:ring-2 hover:ring-slate-300 ${
                  pathname === '/profile' ? 'ring-2 ring-slate-950' : ''
                }`}
              >
                <Avatar name={user?.name} url={user?.avatar_url} className="h-9 w-9 text-sm" />
              </Link>
              <button
                onClick={logout}
                className="whitespace-nowrap rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 transition hover:bg-slate-100"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link to="/signup/business" className={navCls('/signup/business')}>
                For business
              </Link>
              <Link to="/login" className={navCls('/login')}>
                Log in
              </Link>
              <Link
                to="/signup"
                className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-slate-800"
              >
                Sign up
              </Link>
            </>
          )}
        </div>

        {/* ---- phone ---- */}
        <div className="flex items-center gap-2 md:hidden">
          {!isAuthenticated && (
            <Link
              to="/signup"
              className="rounded-lg bg-slate-950 px-3.5 py-2 text-sm font-medium text-white shadow-sm"
            >
              Sign up
            </Link>
          )}
          <button
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-700"
          >
            <Icon name={menuOpen ? 'close' : 'menu'} className="h-5 w-5" />
          </button>
        </div>
      </nav>

      {menuOpen && (
        <div className="border-t border-slate-200 bg-white md:hidden">
          <div className={`${CONTAINER} space-y-4 py-4`}>
            {isAuthenticated && (
              <>
                <Link to="/profile" className="flex items-center gap-3 rounded-xl bg-slate-50 p-3">
                  <Avatar name={user?.name} url={user?.avatar_url} className="h-10 w-10 text-sm" tone="bg-slate-950 text-white" />
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium">{user?.name}</span>
                    <span className="block truncate text-xs text-slate-500">{user?.email}</span>
                  </span>
                </Link>
                <TripSearch />
              </>
            )}
            <ul className="space-y-1">
              {links
                .filter((l) => l.show)
                .map((l) => (
                  <li key={l.to}>
                    <Link
                      to={l.to}
                      className={`flex items-center gap-3 rounded-lg px-3 py-3 text-[15px] ${
                        pathname.startsWith(l.to) ? 'bg-slate-100 font-medium' : 'text-slate-700'
                      }`}
                    >
                      <Icon name={l.icon} className="h-5 w-5 text-slate-400" />
                      {l.label}
                    </Link>
                  </li>
                ))}
            </ul>
            {isAuthenticated ? (
              <button
                onClick={logout}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700"
              >
                <Icon name="logout" className="h-4 w-4" /> Log out
              </button>
            ) : (
              <div className="space-y-2">
                <Link
                  to="/login"
                  className="flex w-full items-center justify-center rounded-xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700"
                >
                  Log in
                </Link>
                <Link
                  to="/signup/business"
                  className="flex w-full items-center justify-center rounded-xl px-4 py-2 text-sm text-slate-600"
                >
                  Register your business
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  )
}

function AdminHeader() {
  const { user, isAuthenticated, isAdmin, logout } = useAuth()

  return (
    <header className="sticky top-0 z-[1200] border-b border-gold/20 bg-ink text-slate-100">
      <nav className={`${CONTAINER} flex h-16 items-center justify-between gap-4`}>
        <Link to="/admin" className="flex items-center gap-2.5 whitespace-nowrap text-base font-semibold">
          <span className="rounded-lg ring-1 ring-white/20">
            <LogoMark className="h-7 w-auto" tile />
          </span>
          <span className="hidden min-[360px]:inline">
            Safarnama <span className="ml-1 rounded-full border border-gold/40 px-2 py-0.5 text-[10px] font-semibold tracking-[0.18em] text-gold uppercase">Admin</span>
          </span>
        </Link>

        <div className="flex items-center gap-2 text-sm sm:gap-4">
          <Link to="/dashboard" className="rounded-lg px-2 py-1.5 text-slate-400 hover:text-slate-100">
            Traveller site
          </Link>
          {isAuthenticated && isAdmin && (
            <>
              <span className="hidden text-slate-400 md:inline">{user?.name}</span>
              <button
                onClick={logout}
                className="whitespace-nowrap rounded-lg border border-white/15 px-3 py-1.5 transition hover:border-gold/60"
              >
                Log out
              </button>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}

/** Help floats on every page for travellers and for people not logged in yet
 *  (login, sign-up, landing). An admin reads support conversations in
 *  /admin/chat-logs instead of having one float over the admin pages. */
function TravellerChat({ inAdmin }: { inAdmin: boolean }) {
  const { isAdmin, isLoading } = useAuth()
  if (inAdmin || isAdmin || isLoading) return null
  return <ChatWidget />
}
