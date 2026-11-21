import { Link } from 'react-router-dom'
import { Icon, type IconName } from '@/components/Icon'
import { formatINR } from '@/features/trips/api'
import type { TripDetail } from '@/features/trips/types'

const SEASON: Record<string, { label: string; tone: string }> = {
  ideal: { label: 'Best time to go', tone: 'bg-emerald-400/15 text-emerald-200 ring-emerald-300/30' },
  pleasant: { label: 'Pleasant weather', tone: 'bg-sky-400/15 text-sky-200 ring-sky-300/30' },
  hot: { label: 'Hot season', tone: 'bg-orange-400/15 text-orange-200 ring-orange-300/30' },
  rainy: { label: 'Monsoon', tone: 'bg-cyan-400/15 text-cyan-200 ring-cyan-300/30' },
  cold: { label: 'Cold season', tone: 'bg-indigo-300/15 text-indigo-100 ring-indigo-200/30' },
}

const BOOK: { to: string; label: string; icon: IconName }[] = [
  { to: 'flights', label: 'Flights', icon: 'plane' },
  { to: 'hotels', label: 'Hotels', icon: 'bed' },
  { to: 'trains', label: 'Trains', icon: 'train' },
  { to: 'buses', label: 'Buses', icon: 'bus' },
]

const day = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })

/**
 * The trip as a boarding pass: the place set large on the left, and a
 * perforated stub on the right with the length of the trip, its dates and
 * what the season will be like. One accent colour (marigold) marks the stub
 * and the main action; everything else stays quiet.
 */
export function TripHero({ trip, exportBar }: { trip: TripDetail; exportBar?: React.ReactNode }) {
  const [city, ...rest] = trip.destination.split(',')
  const thinking = trip.itinerary?.thinking
  const region = rest.join(',').trim() || thinking?.place?.state || null
  const days = Math.round((new Date(`${trip.end_date}T00:00:00`).getTime() - new Date(`${trip.start_date}T00:00:00`).getTime()) / 86_400_000) + 1
  const season = thinking?.seasons?.[0]
  const s = season ? SEASON[season.label] : null

  return (
    <header className="space-y-5">
      <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900">
        <Icon name="back" className="h-4 w-4" /> My trips
      </Link>

      <div className="relative flex flex-col overflow-hidden rounded-[28px] bg-[#1C2452] text-white shadow-[0_20px_50px_-20px_rgba(28,36,82,0.55)] md:flex-row">
        {/* main panel */}
        <div className="relative flex-1 px-7 py-8 sm:px-10 sm:py-10">
          {/* a dotted route curving to the place: the one drawing on the page */}
          <svg viewBox="0 0 420 160" className="pointer-events-none absolute right-0 bottom-0 hidden h-40 w-[420px] text-white/15 lg:block" aria-hidden>
            <path d="M10 150 C 120 150, 140 40, 260 60 S 380 30, 400 20" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="2 9" strokeLinecap="round" />
            <circle cx="400" cy="20" r="5" fill="#F2A93B" />
          </svg>

          <div className="relative">
            {region && <p className="text-[15px] text-white/60">{region}</p>}
            <h1 className="font-display mt-1 text-6xl leading-[0.95] tracking-tight sm:text-7xl">{city.trim()}</h1>
            {trip.role === 'member' && (
              <p className="mt-3 inline-flex rounded-full bg-white/10 px-3 py-1 text-xs text-white/80">You’re travelling with this group</p>
            )}

            <dl className="mt-8 flex flex-wrap gap-x-8 gap-y-4 text-sm">
              <Fact label="Travellers" value={`${trip.travelers}`} icon="users" />
              <Fact label="Budget" value={Number(trip.budget) > 0 ? formatINR(trip.budget) : 'Not set'} icon="wallet" />
              {trip.style_tags.length > 0 && (
                <Fact label="Trip style" value={trip.style_tags.map((t) => t[0].toUpperCase() + t.slice(1)).join(', ')} icon="compass" />
              )}
            </dl>
          </div>
        </div>

        {/* perforation */}
        <div className="relative hidden w-0 md:block" aria-hidden>
          <span className="absolute -top-4 -left-4 h-8 w-8 rounded-full bg-slate-50" />
          <span className="absolute -bottom-4 -left-4 h-8 w-8 rounded-full bg-slate-50" />
          <span className="absolute inset-y-6 left-0 border-l-2 border-dashed border-white/20" />
        </div>
        <div className="border-t-2 border-dashed border-white/20 md:hidden" aria-hidden />

        {/* stub */}
        <div className="flex flex-col justify-between gap-6 px-7 py-8 sm:px-10 md:w-72 md:py-10">
          <div>
            <p className="font-display text-6xl leading-none text-[#F2A93B]">
              {days}
              <span className="ml-2 font-sans text-base text-white/70">{days === 1 ? 'day' : 'days'}</span>
            </p>
            <p className="mt-4 text-[15px] text-white/90">{day(trip.start_date)}</p>
            {days > 1 && <p className="text-[15px] text-white/90">to {day(trip.end_date)}</p>}
          </div>
          {s && season && (
            <span className={`inline-flex w-fit items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ring-1 ${s.tone}`}>
              <Icon name="sun" className="h-3.5 w-3.5" />
              {s.label} ({Math.round(season.confidence * 100)}% sure)
            </span>
          )}
        </div>
      </div>

      {/* actions */}
      <div className="flex flex-wrap items-center gap-3">
        <Link
          to={`/trips/${trip.id}/packing`}
          className="inline-flex items-center gap-2 rounded-xl bg-[#F2A93B] px-5 py-2.5 text-sm font-semibold text-[#1C2452] shadow-sm transition hover:bg-[#f5b85a] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1C2452]"
        >
          <Icon name="luggage" className="h-4 w-4" /> Packing list
        </Link>
        <nav aria-label="Book travel" className="inline-flex rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
          {BOOK.map((b) => (
            <Link
              key={b.to}
              to={`/book/${b.to}?trip=${trip.id}`}
              className="inline-flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 hover:text-slate-950"
            >
              <Icon name={b.icon} className="h-4 w-4 text-slate-500" /> {b.label}
            </Link>
          ))}
        </nav>
        {exportBar && <div className="md:ml-auto">{exportBar}</div>}
      </div>
    </header>
  )
}

function Fact({ label, value, icon }: { label: string; value: string; icon: IconName }) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10">
        <Icon name={icon} className="h-4 w-4 text-white/80" />
      </span>
      <div>
        <dt className="text-xs text-white/55">{label}</dt>
        <dd className="font-medium">{value}</dd>
      </div>
    </div>
  )
}
