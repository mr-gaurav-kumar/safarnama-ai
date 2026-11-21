import { NavLink, Outlet } from 'react-router-dom'
import { Icon, type IconName } from '@/components/Icon'
import { useStats } from './api'

interface Item {
  to: string
  label: string
  icon: IconName
  /** Which stat, if any, shows as a badge on this link. */
  badge?: 'open_fraud_flags' | 'open_escalations' | 'trips_processing' | 'bookings_pending' | 'businesses_pending'
  end?: boolean
}

const GROUPS: { title: string; items: Item[] }[] = [
  {
    title: 'Command',
    items: [{ to: '/admin', label: 'Overview', icon: 'crown', end: true }],
  },
  {
    title: 'Manage',
    items: [
      { to: '/admin/users', label: 'Users', icon: 'users' },
      { to: '/admin/businesses', label: 'Merchants', icon: 'landmark', badge: 'businesses_pending' },
      { to: '/admin/trips', label: 'Trips', icon: 'map', badge: 'trips_processing' },
      { to: '/admin/packages', label: 'Packages', icon: 'bag' },
      { to: '/admin/bookings', label: 'Bookings', icon: 'calendar', badge: 'bookings_pending' },
      { to: '/admin/packing', label: 'Packing defaults', icon: 'check' },
    ],
  },
  {
    title: 'Trust & support',
    items: [
      { to: '/admin/fraud', label: 'Fraud review', icon: 'shield', badge: 'open_fraud_flags' },
      { to: '/admin/escalations', label: 'Escalations', icon: 'bell', badge: 'open_escalations' },
      { to: '/admin/feedback', label: 'Feedback', icon: 'star' },
      { to: '/admin/chat-logs', label: 'Chat logs', icon: 'chat' },
      { to: '/admin/audit', label: 'Audit log', icon: 'activity' },
    ],
  },
]

/**
 * Sidebar plus outlet. The counts come from the same `/admin/stats` query the
 * overview uses, so the queue numbers in the nav and on the page never disagree.
 */
export function AdminLayout() {
  const { data: stats } = useStats()

  return (
    <div className="grid gap-6 lg:grid-cols-[15rem_1fr] lg:gap-10">
      <nav className="-mx-4 overflow-x-auto px-4 sm:-mx-6 sm:px-6 lg:sticky lg:top-24 lg:mx-0 lg:self-start lg:overflow-visible lg:px-0">
        <div className="rounded-2xl bg-ink p-2 lg:p-3 lg:shadow-[0_20px_40px_-20px_rgba(11,16,32,0.6)]">
          <ul className="flex gap-1 whitespace-nowrap lg:flex-col lg:gap-0">
            {GROUPS.map((g) => (
              <li key={g.title} className="flex gap-1 lg:block">
                <p className="hidden px-3 pt-4 pb-2 text-[10px] font-semibold tracking-[0.18em] text-gold/70 uppercase first:pt-1 lg:block">
                  {g.title}
                </p>
                <ul className="flex gap-1 lg:flex-col lg:gap-0.5">
                  {g.items.map((item) => {
                    const count = item.badge ? (stats?.[item.badge] ?? 0) : 0
                    return (
                      <li key={item.to}>
                        <NavLink
                          to={item.to}
                          end={item.end}
                          className={({ isActive }) =>
                            `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                              isActive
                                ? 'bg-white/[0.07] font-medium text-white'
                                : 'text-slate-400 hover:bg-white/[0.04] hover:text-slate-100'
                            }`
                          }
                        >
                          {({ isActive }) => (
                            <>
                              {isActive && (
                                <span className="absolute top-2 bottom-2 left-0 hidden w-0.5 rounded-full bg-gold lg:block" />
                              )}
                              <Icon
                                name={item.icon}
                                className={`h-[18px] w-[18px] ${isActive ? 'text-gold' : 'text-slate-500 group-hover:text-slate-300'}`}
                              />
                              <span className="flex-1">{item.label}</span>
                              {count > 0 && (
                                <span className="rounded-full bg-gold px-1.5 py-px text-[11px] font-semibold text-ink">
                                  {count}
                                </span>
                              )}
                            </>
                          )}
                        </NavLink>
                      </li>
                    )
                  })}
                </ul>
              </li>
            ))}
          </ul>
        </div>
      </nav>

      <div className="min-w-0 space-y-6">
        <Outlet />
      </div>
    </div>
  )
}
