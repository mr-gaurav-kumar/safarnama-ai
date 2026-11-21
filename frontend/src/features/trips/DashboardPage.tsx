import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Icon, type IconName } from '@/components/Icon'
import { useAuth } from '@/lib/auth'
import { VerifyEmailBanner } from '@/components/VerifyEmailBanner'
import { formatDate, formatINR, useDeleteTrip, useTrips } from '@/features/trips/api'
import { useDecline, useInvitations, useJoin } from '@/features/trips/groupApi'
import type { Invitation, Trip } from '@/features/trips/types'

const TILES: { to: string; icon: IconName; label: string; note: string; ready: boolean }[] = [
  { to: '/trips/new', icon: 'spark', label: 'Plan a trip', note: 'A full itinerary in about a minute', ready: true },
  { to: '/trips/new/own', icon: 'file', label: 'Save my own plan', note: 'Write your days yourself, save it and get a PDF', ready: true },
  { to: '/assistant', icon: 'compass', label: 'Ask the assistant', note: 'Places, rough budget and weather for your budget', ready: true },
  { to: '/packages', icon: 'bag', label: 'Packages', note: 'Ready-made trips you can opt into', ready: true },
  { to: '/book/flights', icon: 'train', label: 'Book travel', note: 'Flights, hotels, trains and buses', ready: true },
  { to: '/insights', icon: 'chart', label: 'Tourism insights', note: 'Official Ministry of Tourism data', ready: true },
]

function daysBetween(a: string, b: string): number {
  return Math.round((new Date(`${b}T00:00:00`).getTime() - new Date(`${a}T00:00:00`).getTime()) / 86_400_000)
}

export function DashboardPage() {
  const { user } = useAuth()
  const { data: trips, isPending, isError } = useTrips()
  const [tab, setTab] = useState<'upcoming' | 'past' | 'all'>('upcoming')
  const today = new Date().toISOString().slice(0, 10)
  const all = trips ?? []
  const upcoming = all.filter((t) => t.end_date >= today).sort((a, b) => a.start_date.localeCompare(b.start_date))
  const past = all.filter((t) => t.end_date < today).sort((a, b) => b.start_date.localeCompare(a.start_date))
  const next = upcoming[0]
  const daysToNext = next ? daysBetween(today, next.start_date) : null
  const shown = tab === 'upcoming' ? upcoming : tab === 'past' ? past : all
  const planned = all.reduce((sum, t) => sum + Number(t.budget || 0), 0)
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="space-y-10">
      <VerifyEmailBanner />

      {/* ---------- Greeting ---------- */}
      <header className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="text-sm text-slate-500">{greeting}</p>
          <h1 className="font-display mt-1 text-4xl tracking-tight text-slate-950 sm:text-5xl">
            {user?.name?.split(' ')[0]}
          </h1>
          <p className="mt-2 text-slate-600">
            {next
              ? daysToNext! > 0
                ? `${next.destination} is ${daysToNext} day${daysToNext === 1 ? '' : 's'} away.`
                : `You’re travelling in ${next.destination}.`
              : 'Where are you going next?'}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
        <Link
          to="/trips/new"
          className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
        >
          Plan a new trip <Icon name="arrow" className="h-4 w-4" />
        </Link>
        <Link
          to="/trips/new/own"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-800 shadow-sm transition hover:bg-slate-50"
        >
          <Icon name="file" className="h-4 w-4" /> Save my own plan
        </Link>
        </div>
      </header>

      {/* ---------- Stats ---------- */}
      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-slate-200 bg-slate-200 lg:grid-cols-4">
        {[
          { label: 'Total trips', value: String(all.length) },
          { label: 'Upcoming', value: String(upcoming.length) },
          { label: 'Completed', value: String(past.length) },
          { label: 'Total budget planned', value: formatINR(planned) },
        ].map((s) => (
          <div key={s.label} className="bg-white px-6 py-5">
            <dt className="text-sm text-slate-500">{s.label}</dt>
            <dd className="mt-2 text-2xl font-semibold tracking-tight tabular-nums">{s.value}</dd>
          </div>
        ))}
      </dl>

      {/* ---------- Next trip spotlight ---------- */}
      {next && (
        <Link
          to={`/trips/${next.id}`}
          className="group flex flex-wrap items-center justify-between gap-6 rounded-2xl bg-slate-950 px-6 py-6 text-white transition hover:bg-slate-900 sm:px-8"
        >
          <div className="flex items-center gap-5">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 text-indigo-200">
              <Icon name="pin" className="h-6 w-6" />
            </span>
            <div>
              <p className="text-xs font-medium tracking-wide text-slate-400 uppercase">Next trip</p>
              <p className="font-display text-3xl tracking-tight">{next.destination}</p>
              <p className="mt-0.5 text-sm text-slate-400">
                {formatDate(next.start_date)} – {formatDate(next.end_date)} · {next.travelers} traveller
                {next.travelers > 1 ? 's' : ''} · {formatINR(next.budget)}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-6">
            {daysToNext != null && daysToNext > 0 && (
              <div className="text-right">
                <p className="font-display text-4xl tabular-nums">{daysToNext}</p>
                <p className="text-xs text-slate-400">day{daysToNext === 1 ? '' : 's'} to go</p>
              </div>
            )}
            <span className="flex items-center gap-2 text-sm font-medium text-white/90 group-hover:text-white">
              Open itinerary <Icon name="arrow" className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </span>
          </div>
        </Link>
      )}

      <Invitations />

      <RateNudge trips={all} />

      {/* ---------- Trips ---------- */}
      <section>
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold tracking-tight">Your trips</h2>
          <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 text-sm">
            {([
              ['upcoming', `Upcoming (${upcoming.length})`],
              ['past', `Past (${past.length})`],
              ['all', `All (${all.length})`],
            ] as const).map(([k, label]) => (
              <button
                key={k}
                type="button"
                onClick={() => setTab(k)}
                className={`rounded-md px-3 py-1.5 transition ${
                  tab === k ? 'bg-slate-950 font-medium text-white' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {isPending && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-44 animate-pulse rounded-2xl bg-slate-200/60" />
            ))}
          </div>
        )}
        {isError && <p className="text-sm text-red-700">Could not load your trips.</p>}
        {trips && shown.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
            <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border border-slate-200 text-slate-500">
              <Icon name="map" className="h-6 w-6" />
            </span>
            <p className="mt-4 font-medium">
              {tab === 'past' ? 'No past trips yet' : tab === 'upcoming' ? 'No upcoming trips' : 'No trips yet'}
            </p>
            <p className="mt-1 text-sm text-slate-500">Plan one — it takes about a minute.</p>
            <Link
              to="/trips/new"
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800"
            >
              Plan a trip <Icon name="arrow" className="h-4 w-4" />
            </Link>
          </div>
        )}
        {trips && shown.length > 0 && (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {shown.map((trip) => (
              <TripCard key={trip.id} trip={trip} today={today} />
            ))}
          </ul>
        )}
      </section>

      {/* ---------- Shortcuts ---------- */}
      <section>
        <h2 className="mb-5 text-xl font-semibold tracking-tight">Shortcuts</h2>
        <div className="grid gap-px overflow-hidden rounded-2xl border border-slate-200 bg-slate-200 sm:grid-cols-2 lg:grid-cols-3">
          {TILES.map((tile) => (
            <Link key={tile.label} to={tile.to} className="group bg-white p-6 transition hover:bg-slate-50">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-indigo-700">
                <Icon name={tile.icon} />
              </span>
              <span className="mt-5 flex items-center gap-1.5 font-medium">
                {tile.label}
                <Icon name="arrow" className="h-3.5 w-3.5 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-slate-900" />
              </span>
              <span className="mt-1 block text-sm text-slate-500">{tile.note}</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}

function TripCard({ trip, today }: { trip: Trip; today: string }) {
  const deleteTrip = useDeleteTrip()
  const [confirming, setConfirming] = useState(false)
  const isPast = trip.end_date < today
  const days = daysBetween(trip.start_date, trip.end_date) + 1

  const badge =
    trip.status === 'processing'
      ? { text: 'Planning…', cls: 'bg-amber-50 text-amber-700 ring-amber-200' }
      : trip.status === 'failed'
        ? { text: 'Failed', cls: 'bg-red-50 text-red-700 ring-red-200' }
        : isPast
          ? { text: 'Completed', cls: 'bg-slate-100 text-slate-600 ring-slate-200' }
          : { text: 'Upcoming', cls: 'bg-emerald-50 text-emerald-700 ring-emerald-200' }

  return (
    <li className="group flex flex-col rounded-2xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition hover:border-slate-300 hover:shadow-[0_12px_28px_-14px_rgba(15,23,42,0.25)]">
      <Link to={`/trips/${trip.id}`} className="flex flex-1 flex-col p-5">
        <div className="flex items-start justify-between gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-sm font-semibold text-slate-700">
            {trip.destination.trim()[0]?.toUpperCase()}
          </span>
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ${badge.cls}`}>{badge.text}</span>
        </div>
        <p className="mt-4 truncate text-lg font-semibold tracking-tight">{trip.destination}</p>
        <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-500">
          <Icon name="calendar" className="h-4 w-4" />
          {formatDate(trip.start_date)} – {formatDate(trip.end_date)}
        </p>
        <div className="mt-4 flex items-center gap-4 text-sm text-slate-600">
          <span>{days} day{days > 1 ? 's' : ''}</span>
          <span className="h-1 w-1 rounded-full bg-slate-300" />
          <span className="flex items-center gap-1.5">
            <Icon name="users" className="h-4 w-4 text-slate-400" /> {trip.travelers}
          </span>
          <span className="h-1 w-1 rounded-full bg-slate-300" />
          <span className="font-medium text-slate-900 tabular-nums">{formatINR(trip.budget)}</span>
        </div>
        {(trip.style_tags.length > 0 || trip.role === 'member' || trip.member_count > 0) && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {trip.role === 'member' && <Tag>Shared with you</Tag>}
            {trip.role === 'owner' && trip.member_count > 0 && (
              <Tag>+{trip.member_count} {trip.member_count === 1 ? 'person' : 'people'}</Tag>
            )}
            {trip.style_tags.map((t) => (
              <Tag key={t}>{t}</Tag>
            ))}
          </div>
        )}
      </Link>

      <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 text-sm">
        <span className="flex flex-wrap items-center gap-4">
          <Link to={`/trips/${trip.id}/packing`} className="font-medium text-indigo-700 hover:text-indigo-900">
            🧳 Packing
          </Link>
          {(['flights', 'hotels', 'trains', 'buses'] as const).map((m) => (
            <Link key={m} to={`/book/${m}?trip=${trip.id}`} className="font-medium capitalize text-slate-600 hover:text-slate-900">
              {m}
            </Link>
          ))}
        </span>
        {trip.role === 'owner' &&
          (confirming ? (
            <span className="flex items-center gap-3">
              <button
                onClick={() => deleteTrip.mutate(trip.id)}
                disabled={deleteTrip.isPending}
                className="font-medium text-red-600 hover:text-red-700 disabled:opacity-50"
              >
                Confirm delete
              </button>
              <button onClick={() => setConfirming(false)} className="text-slate-500 hover:text-slate-900">
                Cancel
              </button>
            </span>
          ) : (
            <button onClick={() => setConfirming(true)} className="text-slate-400 hover:text-red-600">
              Delete
            </button>
          ))}
      </div>
    </li>
  )
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-slate-200 px-2.5 py-0.5 text-xs capitalize text-slate-600">{children}</span>
  )
}

function Invitations() {
  const { data } = useInvitations()
  if (!data || data.length === 0) return null
  return (
    <section>
      <h2 className="mb-4 text-xl font-semibold tracking-tight">Invitations</h2>
      <ul className="space-y-3">
        {data.map((inv) => (
          <InvitationRow key={inv.trip_id} inv={inv} />
        ))}
      </ul>
    </section>
  )
}

function InvitationRow({ inv }: { inv: Invitation }) {
  const join = useJoin(inv.trip_id)
  const decline = useDecline(inv.trip_id)
  return (
    <li className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4">
      <span className="flex-1">
        <span className="block font-medium">
          {inv.invited_by} invited you to {inv.destination}
        </span>
        <span className="text-sm text-slate-500">
          {formatDate(inv.start_date)} – {formatDate(inv.end_date)}
        </span>
      </span>
      <button
        onClick={() => join.mutate(null)}
        disabled={join.isPending}
        className="rounded-lg bg-slate-950 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
      >
        Join
      </button>
      <button
        onClick={() => decline.mutate(null)}
        disabled={decline.isPending}
        className="text-sm text-slate-500 hover:text-slate-900"
      >
        Decline
      </button>
    </li>
  )
}

/** Past trips you haven't rated yet -- the feedback loop needs the rating. */
function RateNudge({ trips }: { trips: Trip[] }) {
  const today = new Date().toISOString().slice(0, 10)
  const unrated = trips.filter(
    (t) => t.status === 'completed' && t.end_date < today && t.my_rating == null,
  )
  if (unrated.length === 0) return null
  const first = unrated[0]
  return (
    <p className="rounded-2xl border border-slate-200 bg-white px-5 py-4 text-sm">
      How was <b>{first.destination}</b>?{' '}
      <Link to={`/trips/${first.id}`} className="underline">
        Rate it
      </Link>{' '}
      <span className="text-slate-500">— it makes your next plans better.</span>
      {unrated.length > 1 && <span className="text-slate-500"> ({unrated.length - 1} more to rate)</span>}
    </p>
  )
}
