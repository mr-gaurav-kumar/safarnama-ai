/**
 * Pieces every booking page shares: the Flights / Hotels / Trains / Buses
 * tabs, "fill from a trip", and the list of outside sites to search on.
 */
import { useMemo, useState, type ReactNode } from 'react'
import { NavLink, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { Icon, type IconName } from '@/components/Icon'
import { formatDate, useTrips } from '@/features/trips/api'
import type { Trip } from '@/features/trips/types'
import type { Provider } from './providers'

export const cityOnly = (s: string) => s.split(',')[0].trim()
export const todayIso = () => new Date().toISOString().slice(0, 10)
export const addDays = (iso: string, n: number) => {
  const d = new Date(`${iso}T00:00:00`)
  d.setDate(d.getDate() + n)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
/** A date in the past is no use to a booking site: move it to today. */
export const notPast = (iso: string) => (iso < todayIso() ? todayIso() : iso)

export const inputCls =
  'w-full rounded-xl border border-slate-200 px-3.5 py-3 text-[15px] outline-none focus:border-slate-900'

// ---------------------------------------------------------------- tabs

const TABS: { to: string; label: string; icon: IconName }[] = [
  { to: '/book/flights', label: 'Flights', icon: 'arrow' },
  { to: '/book/hotels', label: 'Hotels', icon: 'home' },
  { to: '/book/trains', label: 'Trains', icon: 'train' },
  { to: '/book/buses', label: 'Buses', icon: 'map' },
]

/** Keeps ?trip= when switching tabs, so the chosen trip follows you. */
export function BookingTabs() {
  const [params] = useSearchParams()
  const trip = params.get('trip')
  return (
    <nav className="inline-flex flex-wrap rounded-xl border border-slate-200 bg-white p-1 text-sm">
      {TABS.map((t) => (
        <NavLink
          key={t.to}
          to={trip ? `${t.to}?trip=${trip}` : t.to}
          className={({ isActive }) =>
            `flex items-center gap-2 rounded-lg px-4 py-2 ${isActive ? 'bg-slate-950 font-medium text-white' : 'text-slate-600 hover:text-slate-900'}`
          }
        >
          <Icon name={t.icon} className={`h-4 w-4 ${t.icon === 'arrow' ? '-rotate-45' : ''}`} />
          {t.label}
        </NavLink>
      ))}
    </nav>
  )
}

export function BookingHeader({ eyebrow, title, subtitle }: { eyebrow: string; title: string; subtitle: string }) {
  return (
    <header className="space-y-6">
      <BookingTabs />
      <div>
        <p className="text-sm font-medium text-indigo-700">{eyebrow}</p>
        <h1 className="font-display mt-1 text-4xl tracking-tight sm:text-5xl">{title}</h1>
        <p className="mt-2 max-w-2xl text-slate-600">{subtitle}</p>
      </div>
    </header>
  )
}

// ---------------------------------------------------------------- trip prefill

/** The trip picked in ?trip=, the user's upcoming trips, and their home town. */
export function useTripPrefill() {
  const { user } = useAuth()
  const { data: trips = [] } = useTrips()
  const [params, setParams] = useSearchParams()
  const upcoming = useMemo(
    () => [...trips].filter((t) => t.end_date >= todayIso()).sort((a, b) => a.start_date.localeCompare(b.start_date)),
    [trips],
  )
  const tripId = params.get('trip') ?? ''
  const trip: Trip | undefined = trips.find((t) => t.id === tripId)
  const setTripId = (id: string) => setParams(id ? { trip: id } : {})
  return { trip, tripId, setTripId, upcoming, home: user?.home_town ?? '' }
}

export function TripPicker({
  upcoming, tripId, setTripId, children,
}: { upcoming: Trip[]; tripId: string; setTripId: (id: string) => void; children?: ReactNode }) {
  if (upcoming.length === 0) return null
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <span className="text-sm font-medium text-slate-700">Fill from a trip</span>
      <select
        value={tripId}
        onChange={(e) => setTripId(e.target.value)}
        className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-900 sm:flex-none"
      >
        <option value="">Choose a trip…</option>
        {upcoming.map((t) => (
          <option key={t.id} value={t.id}>
            {t.destination} · {formatDate(t.start_date)}
          </option>
        ))}
      </select>
      {children}
    </div>
  )
}

export function DirectionToggle({ value, onChange }: { value: 'go' | 'return'; onChange: (v: 'go' | 'return') => void }) {
  return (
    <div className="inline-flex rounded-lg bg-slate-100 p-1 text-sm">
      {(['go', 'return'] as const).map((d) => (
        <button
          key={d}
          type="button"
          onClick={() => onChange(d)}
          className={`rounded-md px-3 py-1 ${value === d ? 'bg-white font-medium shadow-sm' : 'text-slate-600'}`}
        >
          {d === 'go' ? 'Onward' : 'Return'}
        </button>
      ))}
    </div>
  )
}

export function NumberField({
  label, value, onChange, min = 1, max = 9,
}: { label: string; value: number; onChange: (n: number) => void; min?: number; max?: number }) {
  return (
    <label className="block text-sm">
      <span className="mb-2 block font-medium text-slate-800">{label}</span>
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Math.min(max, Math.max(min, Number(e.target.value) || min)))}
        className={inputCls}
      />
    </label>
  )
}

// ---------------------------------------------------------------- providers

export interface Detail {
  label: string
  value: string
}

/**
 * One card per outside site. Sites that take a search link open with the
 * journey filled in; the rest open their search page, and the details row
 * above lets the user copy each value across.
 */
export function ProviderList<Q>({
  providers, query, details, problem,
}: {
  providers: Provider<Q>[]
  query: Q | null
  details: Detail[]
  /** Why the search isn't ready yet, e.g. "Pick an airport for To". */
  problem: string | null
}) {
  const [copied, setCopied] = useState<string | null>(null)
  async function copy(d: Detail) {
    try {
      await navigator.clipboard.writeText(d.value)
      setCopied(d.label)
      setTimeout(() => setCopied(null), 1500)
    } catch {
      /* clipboard blocked */
    }
  }
  const ready = query !== null && !problem

  return (
    <section className="space-y-4">
      {ready ? (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-slate-500">Your search:</span>
          {details.map((d) => (
            <button
              key={d.label}
              type="button"
              onClick={() => copy(d)}
              title="Copy"
              className="rounded-full border border-slate-200 bg-white px-3 py-1 text-slate-700 hover:border-slate-400"
            >
              <span className="text-slate-400">{d.label}:</span> {copied === d.label ? 'Copied ✓' : d.value}
            </button>
          ))}
        </div>
      ) : (
        <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">{problem ?? 'Fill in the search above.'}</p>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {providers.map((p) => (
          <article key={p.id} className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div>
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold">{p.name}</h3>
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${p.prefilled ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}
                >
                  {p.prefilled ? 'Details filled in' : 'Copy details'}
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-500">{p.blurb}</p>
            </div>
            <a
              href={ready ? p.url(query as Q) : undefined}
              target="_blank"
              rel="noopener noreferrer"
              aria-disabled={!ready}
              onClick={(e) => !ready && e.preventDefault()}
              className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold ${
                ready ? 'bg-slate-950 text-white hover:bg-slate-800' : 'cursor-not-allowed bg-slate-200 text-slate-400'
              }`}
            >
              Search on {p.name} <Icon name="arrow" className="h-4 w-4 -rotate-45" />
            </a>
          </article>
        ))}
      </div>

      <p className="text-xs leading-relaxed text-slate-400">
        Prices, availability and booking are on the partner site — Safarnama doesn’t take payment for these. Always check
        the final price and cancellation rules there before you pay.
      </p>
    </section>
  )
}
