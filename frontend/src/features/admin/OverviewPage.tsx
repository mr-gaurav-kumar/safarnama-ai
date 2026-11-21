import { Link } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { Icon, type IconName } from '@/components/Icon'
import { formatWhen, useAdminBookings, useAudit, useStats, useUsers } from './api'
import type { Stats } from './types'

const INR = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

interface Kpi {
  key: keyof Stats
  label: string
  to: string
  icon: IconName
  sub?: (s: Stats) => string
}

const KPIS: Kpi[] = [
  { key: 'users_total', label: 'Travellers', to: '/admin/users', icon: 'users', sub: (s) => `+${s.signups_7d} this week` },
  { key: 'trips_total', label: 'Trips planned', to: '/admin/trips', icon: 'map', sub: (s) => `${s.trips_active} still ahead` },
  { key: 'packages_active', label: 'Live packages', to: '/admin/packages', icon: 'bag', sub: () => 'Visible to everyone' },
  { key: 'bookings_pending', label: 'Bookings to confirm', to: '/admin/bookings', icon: 'calendar', sub: () => 'Awaiting your decision' },
]

interface Queue {
  key: keyof Stats
  label: string
  to: string
  icon: IconName
  calm: string
}

const QUEUES: Queue[] = [
  { key: 'businesses_pending', label: 'Business applications', to: '/admin/businesses', icon: 'landmark', calm: 'None waiting' },
  { key: 'bookings_pending', label: 'Package bookings', to: '/admin/bookings', icon: 'calendar', calm: 'All confirmed' },
  { key: 'open_fraud_flags', label: 'Fraud flags', to: '/admin/fraud', icon: 'shield', calm: 'Nothing suspicious' },
  { key: 'open_escalations', label: 'Support escalations', to: '/admin/escalations', icon: 'bell', calm: 'No one waiting' },
  { key: 'trips_processing', label: 'Trips planning now', to: '/admin/trips', icon: 'activity', calm: 'Nothing in progress' },
  { key: 'users_blocked', label: 'Blocked accounts', to: '/admin/users', icon: 'lock', calm: 'None blocked' },
]

function greeting(): string {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
}

function prettyAction(a: string): string {
  return a.replace('.', ' · ').replace(/_/g, ' ')
}

export function OverviewPage() {
  const { user } = useAuth()
  const { data: s, isError } = useStats()
  const users = useUsers('', 5, 0)
  const bookings = useAdminBookings('', 5, 0)
  const audit = useAudit(7, 0)

  const attention = s ? QUEUES.reduce((n, q) => n + (q.key === 'users_blocked' ? 0 : s[q.key]), 0) : 0
  const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

  return (
    <div className="space-y-8">
      {/* ---------------- Hero ---------------- */}
      <section className="relative overflow-hidden rounded-3xl bg-ink px-6 py-8 text-white sm:px-10 sm:py-10">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage:
              'linear-gradient(to right, #e8d3a2 1px, transparent 1px), linear-gradient(to bottom, #e8d3a2 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />
        <div aria-hidden className="pointer-events-none absolute -top-32 -right-24 h-96 w-96 rounded-full bg-gold/25 blur-[110px]" />
        <div aria-hidden className="pointer-events-none absolute -bottom-40 -left-24 h-96 w-96 rounded-full bg-indigo-500/20 blur-[120px]" />
        <div aria-hidden className="pointer-events-none absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-gold/60 to-transparent" />

        <div className="relative flex flex-wrap items-end justify-between gap-8">
          <div>
            <p className="flex items-center gap-2 text-xs font-semibold tracking-[0.2em] text-gold uppercase">
              <Icon name="crown" className="h-4 w-4" /> Command centre
            </p>
            <h1 className="font-display mt-3 text-4xl leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              {greeting()}, <em className="text-gold-light">{user?.name?.split(' ')[0]}</em>
            </h1>
            <p className="mt-3 text-slate-400">
              {today} ·{' '}
              {s == null
                ? 'loading the numbers…'
                : attention > 0
                  ? `${attention} item${attention === 1 ? '' : 's'} need${attention === 1 ? 's' : ''} your attention.`
                  : 'Everything is in order.'}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <QuickAction to="/admin/packages" icon="plus" label="New package" primary />
            <QuickAction to="/admin/users" icon="users" label="Add user" />
            <QuickAction to="/admin/bookings" icon="calendar" label="Bookings" />
          </div>
        </div>

        {/* KPI strip inside the hero */}
        <dl className="relative mt-10 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 lg:grid-cols-4">
          {KPIS.map((k) => (
            <Link key={k.key} to={k.to} className="group bg-ink/95 p-5 transition hover:bg-[#121937] sm:p-6">
              <dt className="flex items-center justify-between text-sm text-slate-400">
                {k.label}
                <Icon name={k.icon} className="h-4 w-4 text-gold/70 transition group-hover:text-gold" />
              </dt>
              <dd className="font-display mt-3 text-4xl tracking-tight tabular-nums text-white sm:text-5xl">
                {s ? s[k.key] : '—'}
              </dd>
              <p className="mt-1 text-xs text-slate-500">{s && k.sub ? k.sub(s) : ' '}</p>
            </Link>
          ))}
        </dl>
      </section>

      {isError && <p className="text-sm text-red-700">Could not load the numbers.</p>}

      <div className="grid gap-6 xl:grid-cols-[1.1fr_1fr]">
        {/* ---------------- Needs attention ---------------- */}
        <Panel title="Needs attention" subtitle="Queues waiting on you">
          <ul className="divide-y divide-slate-100">
            {QUEUES.map((q) => {
              const n = s?.[q.key] ?? 0
              const hot = n > 0 && q.key !== 'users_blocked'
              return (
                <li key={q.key}>
                  <Link to={q.to} className="group flex items-center gap-4 px-6 py-4 transition hover:bg-slate-50">
                    <span
                      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ring-1 ${
                        hot ? 'bg-gold/10 text-gold-dark ring-gold/40' : 'bg-slate-50 text-slate-400 ring-slate-200'
                      }`}
                    >
                      <Icon name={q.icon} className="h-5 w-5" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-slate-900">{q.label}</span>
                      <span className="block text-xs text-slate-500">{n > 0 ? `${n} open` : q.calm}</span>
                    </span>
                    <span
                      className={`font-display text-3xl tabular-nums ${hot ? 'text-gold-dark' : 'text-slate-300'}`}
                    >
                      {s ? n : '—'}
                    </span>
                    <Icon name="arrow" className="h-4 w-4 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-slate-900" />
                  </Link>
                </li>
              )
            })}
          </ul>
        </Panel>

        {/* ---------------- Latest bookings ---------------- */}
        <Panel title="Latest bookings" subtitle="Package requests" to="/admin/bookings">
          {bookings.data?.items.length ? (
            <ul className="divide-y divide-slate-100">
              {bookings.data.items.map((b) => (
                <li key={b.id} className="flex items-center gap-4 px-6 py-3.5">
                  <Avatar name={b.user_name ?? '?'} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{b.package_title}</span>
                    <span className="block truncate text-xs text-slate-500">
                      {b.user_name} · {b.travelers} traveller{b.travelers > 1 ? 's' : ''} · {INR.format(b.total_price)}
                    </span>
                  </span>
                  <StatusPill status={b.status} />
                </li>
              ))}
            </ul>
          ) : (
            <Empty text={bookings.isPending ? 'Loading…' : 'No bookings yet.'} />
          )}
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        {/* ---------------- New travellers ---------------- */}
        <Panel title="Newest travellers" subtitle="Recent sign-ups" to="/admin/users">
          {users.data?.items.length ? (
            <ul className="divide-y divide-slate-100">
              {users.data.items.map((u) => (
                <li key={u.id} className="flex items-center gap-4 px-6 py-3.5">
                  <Avatar name={u.name} />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2 text-sm font-medium">
                      <span className="truncate">{u.name}</span>
                      {u.role === 'admin' && (
                        <span className="rounded-full bg-gold/15 px-2 py-px text-[10px] font-semibold tracking-wide text-gold-dark uppercase">
                          Admin
                        </span>
                      )}
                    </span>
                    <span className="block truncate text-xs text-slate-500">
                      {u.email}
                      {u.home_town ? ` · ${u.home_town}` : ''}
                    </span>
                  </span>
                  <span className="hidden text-xs text-slate-400 sm:block">{formatWhen(u.created_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <Empty text={users.isPending ? 'Loading…' : 'No users yet.'} />
          )}
        </Panel>

        {/* ---------------- Activity ---------------- */}
        <Panel title="Recent admin activity" subtitle="From the audit log" to="/admin/audit">
          {audit.data?.items.length ? (
            <ol className="relative space-y-5 px-6 py-5 before:absolute before:top-6 before:bottom-6 before:left-[29px] before:w-px before:bg-slate-200">
              {audit.data.items.map((a) => (
                <li key={a.id} className="relative flex gap-4 pl-0">
                  <span className="relative z-10 mt-1 h-2.5 w-2.5 shrink-0 rounded-full border-2 border-white bg-gold ring-1 ring-gold/40" />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium capitalize text-slate-900">{prettyAction(a.action)}</span>
                    <span className="block truncate text-xs text-slate-500">
                      {formatWhen(a.created_at)}
                      {typeof a.details?.email === 'string' ? ` · ${a.details.email}` : ''}
                      {typeof a.details?.title === 'string' ? ` · ${a.details.title}` : ''}
                      {typeof a.details?.destination === 'string' ? ` · ${a.details.destination}` : ''}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            <Empty text={audit.isPending ? 'Loading…' : 'No admin actions yet.'} />
          )}
        </Panel>
      </div>
    </div>
  )
}

function QuickAction({ to, icon, label, primary }: { to: string; icon: IconName; label: string; primary?: boolean }) {
  return (
    <Link
      to={to}
      className={`inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
        primary
          ? 'bg-gradient-to-b from-gold-light to-gold text-ink shadow-[0_8px_24px_-8px_rgba(201,164,92,0.7)] hover:brightness-105'
          : 'border border-white/15 text-slate-200 hover:border-gold/60 hover:text-white'
      }`}
    >
      <Icon name={icon} className="h-4 w-4" />
      {label}
    </Link>
  )
}

function Panel({
  title,
  subtitle,
  to,
  children,
}: {
  title: string
  subtitle: string
  to?: string
  children: React.ReactNode
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_32px_-18px_rgba(11,16,32,0.25)]">
      <header className="flex items-center justify-between gap-4 border-b border-slate-100 px-6 py-4">
        <div>
          <h2 className="font-display text-2xl tracking-tight text-slate-950">{title}</h2>
          <p className="text-xs text-slate-500">{subtitle}</p>
        </div>
        {to && (
          <Link to={to} className="flex items-center gap-1 text-sm font-medium text-gold-dark hover:text-slate-950">
            View all <Icon name="arrow" className="h-3.5 w-3.5" />
          </Link>
        )}
      </header>
      {children}
    </section>
  )
}

function Avatar({ name }: { name: string }) {
  const initials = name.split(/\s+/).map((p) => p[0]).join('').slice(0, 2).toUpperCase()
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink text-xs font-semibold text-gold-light ring-2 ring-gold/20">
      {initials}
    </span>
  )
}

const PILL: Record<string, string> = {
  pending: 'bg-gold/10 text-gold-dark ring-gold/40',
  confirmed: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  cancelled: 'bg-slate-100 text-slate-500 ring-slate-200',
}

function StatusPill({ status }: { status: string }) {
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ring-1 ${PILL[status] ?? PILL.cancelled}`}>
      {status}
    </span>
  )
}

function Empty({ text }: { text: string }) {
  return <p className="px-6 py-10 text-center text-sm text-slate-400">{text}</p>
}
