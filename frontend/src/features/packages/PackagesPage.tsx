import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { apiErrorMessage } from '@/lib/auth'
import { Icon } from '@/components/Icon'
import { coverTone, mediaUrl } from '@/lib/media'
import { INR, fmtDate, useCancelBooking, useMyBookings, usePackages, type PackageBooking, type TravelPackage } from './api'

export function PackagesPage() {
  const { isAuthenticated } = useAuth()
  const { data, isPending, isError } = usePackages()
  const [tab, setTab] = useState<'browse' | 'mine'>('browse')
  const [query, setQuery] = useState('')
  const [maxDays, setMaxDays] = useState(0)

  const list = (data ?? []).filter((p) => {
    const q = query.trim().toLowerCase()
    const text = `${p.title} ${p.destination} ${p.style_tags.join(' ')}`.toLowerCase()
    return (!q || text.includes(q)) && (!maxDays || p.duration_days <= maxDays)
  })

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="text-sm font-medium text-indigo-700">Packages</p>
          <h1 className="font-display mt-1 text-4xl tracking-tight sm:text-5xl">Ready-made trips</h1>
          <p className="mt-2 max-w-xl text-slate-600">
            Curated itineraries with stays and transport sorted. Pick one, choose your dates, and opt in.
          </p>
        </div>
        {isAuthenticated && (
          <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 text-sm">
            {(['browse', 'mine'] as const).map((k) => (
              <button
                key={k}
                onClick={() => setTab(k)}
                className={`rounded-md px-4 py-1.5 ${tab === k ? 'bg-slate-950 font-medium text-white' : 'text-slate-600'}`}
              >
                {k === 'browse' ? 'Browse' : 'My bookings'}
              </button>
            ))}
          </div>
        )}
      </header>

      {tab === 'mine' ? (
        <MyBookings />
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative w-full sm:w-80">
              <span className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-slate-400">
                <Icon name="pin" className="h-4 w-4" />
              </span>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Search packages"
                placeholder="Destination or style"
                className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pr-3 pl-10 text-sm outline-none focus:border-slate-900"
              />
            </div>
            <select
              value={maxDays}
              onChange={(e) => setMaxDays(Number(e.target.value))}
              aria-label="Duration"
              className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-slate-900"
            >
              <option value={0}>Any length</option>
              <option value={3}>Up to 3 days</option>
              <option value={5}>Up to 5 days</option>
              <option value={7}>Up to a week</option>
            </select>
          </div>

          {isPending && (
            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {[0, 1, 2].map((i) => <div key={i} className="h-72 animate-pulse rounded-2xl bg-slate-200/60" />)}
            </div>
          )}
          {isError && <p className="text-sm text-red-700">Could not load packages.</p>}
          {data && list.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
              <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border border-slate-200 text-slate-500">
                <Icon name="map" className="h-6 w-6" />
              </span>
              <p className="mt-4 font-medium">{data.length === 0 ? 'No packages yet' : 'Nothing matches that'}</p>
              <p className="mt-1 text-sm text-slate-500">
                {data.length === 0 ? 'New packages will appear here soon.' : 'Try another destination or length.'}
              </p>
            </div>
          )}
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {list.map((p) => <PackageCard key={p.id} pkg={p} />)}
          </div>
        </>
      )}
    </div>
  )
}

function PackageCard({ pkg }: { pkg: TravelPackage }) {
  const soldOut = pkg.seats_left === 0
  return (
    <Link
      to={`/packages/${pkg.id}`}
      className="group flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition hover:border-slate-300 hover:shadow-[0_16px_32px_-16px_rgba(15,23,42,0.25)]"
    >
      <div className={`relative flex h-48 items-end overflow-hidden bg-gradient-to-br p-5 text-white ${coverTone(pkg.title)}`}>
        {pkg.images?.[0] ? (
          <img
            src={mediaUrl(pkg.images[0])}
            alt=""
            loading="lazy"
            className="absolute inset-0 h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
          />
        ) : (
          <div aria-hidden className="absolute -top-16 -right-10 h-48 w-48 rounded-full bg-indigo-500/30 blur-3xl" />
        )}
        <div aria-hidden className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/20 to-transparent" />
        <div className="relative">
          <p className="flex items-center gap-1.5 text-xs text-slate-300">
            <Icon name="pin" className="h-3.5 w-3.5" /> {pkg.destination}
          </p>
          <h3 className="font-display mt-1 text-2xl leading-tight tracking-tight">{pkg.title}</h3>
        </div>
        <span className="absolute top-4 right-4 rounded-full bg-white/10 px-2.5 py-1 text-xs ring-1 ring-white/20">
          {pkg.duration_days} days
        </span>
      </div>
      <div className="flex flex-1 flex-col p-5">
        <p className="mb-2 text-xs text-slate-500">
          by <span className="font-medium text-slate-700">{pkg.business_name ?? 'Safarnama'}</span>
        </p>
        {pkg.summary && <p className="line-clamp-2 text-sm text-slate-600">{pkg.summary}</p>}
        {pkg.inclusions.length > 0 && (
          <ul className="mt-4 space-y-1.5 text-sm text-slate-700">
            {pkg.inclusions.slice(0, 3).map((i) => (
              <li key={i} className="flex items-center gap-2">
                <Icon name="check" className="h-3.5 w-3.5 text-emerald-600" /> {i}
              </li>
            ))}
          </ul>
        )}
        <div className="mt-auto flex items-end justify-between gap-3 pt-5">
          <div>
            <p className="text-xs text-slate-500">From</p>
            <p className="text-xl font-semibold tracking-tight">
              {INR.format(pkg.price_per_person)}
              <span className="text-sm font-normal text-slate-500"> / person</span>
            </p>
          </div>
          {soldOut ? (
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">Sold out</span>
          ) : (
            <span className="flex items-center gap-1.5 text-sm font-medium text-slate-900">
              View <Icon name="arrow" className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </span>
          )}
        </div>
      </div>
    </Link>
  )
}

const STATUS_STYLE: Record<string, string> = {
  pending: 'bg-amber-50 text-amber-700 ring-amber-200',
  confirmed: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  cancelled: 'bg-slate-100 text-slate-500 ring-slate-200',
}

function MyBookings() {
  const { data, isPending } = useMyBookings(true)
  if (isPending) return <p className="text-sm text-slate-500">Loading…</p>
  if (!data || data.length === 0) {
    return (
      <p className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center text-sm text-slate-500">
        You haven’t opted into any package yet.
      </p>
    )
  }
  return (
    <ul className="space-y-3">
      {data.map((b) => <BookingRow key={b.id} b={b} />)}
    </ul>
  )
}

function BookingRow({ b }: { b: PackageBooking }) {
  const cancel = useCancelBooking()
  const [armed, setArmed] = useState(false)
  return (
    <li className="flex flex-wrap items-center gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-4">
      <div className="min-w-0 flex-1">
        <Link to={`/packages/${b.package_id}`} className="font-semibold hover:underline">{b.package_title}</Link>
        <p className="text-sm text-slate-500">
          {fmtDate(b.start_date)} – {fmtDate(b.end_date)} · {b.travelers} traveller{b.travelers > 1 ? 's' : ''} · {INR.format(b.total_price)}
        </p>
        {cancel.error != null && <p className="mt-1 text-xs text-red-600">{apiErrorMessage(cancel.error, 'Could not cancel.')}</p>}
      </div>
      <span className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ring-1 ${STATUS_STYLE[b.status]}`}>{b.status}</span>
      {b.status !== 'cancelled' &&
        (armed ? (
          <span className="flex gap-3 text-sm">
            <button onClick={() => cancel.mutate(b.id)} className="font-medium text-red-600">Confirm cancel</button>
            <button onClick={() => setArmed(false)} className="text-slate-500">Keep</button>
          </span>
        ) : (
          <button onClick={() => setArmed(true)} className="text-sm text-slate-500 hover:text-red-600">Cancel</button>
        ))}
    </li>
  )
}
