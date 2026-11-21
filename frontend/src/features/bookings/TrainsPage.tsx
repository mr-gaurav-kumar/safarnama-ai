import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '@/lib/api'
import { apiErrorMessage, useAuth } from '@/lib/auth'
import { Icon } from '@/components/Icon'
import { formatDate, useTrips } from '@/features/trips/api'
import { BookingTabs } from './shared'

const IRCTC_URL = 'https://www.irctc.co.in/nget/train-search'
const BUS_SITES = [
  { name: 'redBus', url: 'https://www.redbus.in/' },
  { name: 'AbhiBus', url: 'https://www.abhibus.com/' },
]

interface Station {
  code: string
  name: string
  state: string | null
}

interface Train {
  number: string
  name: string | null
  from_code: string
  from_name: string | null
  to_code: string
  to_name: string | null
  departs: string | null
  arrives: string | null
  arrives_day_offset: number | null
  duration: string | null
  classes: string[]
  run_days: string[]
  train_type: string | null
}

const cityOnly = (s: string) => s.split(',')[0].trim()
const todayIso = () => new Date().toISOString().slice(0, 10)
const ddmmyyyy = (iso: string) => iso.split('-').reverse().join('/')

/**
 * Trains and buses for a trip. With a RapidAPI key in .env, trains are
 * searched live right here; without one (and for buses, which have no free
 * API) the page fills in the journey and opens IRCTC / redBus.
 */
export function TrainsPage() {
  const { user } = useAuth()
  const { data: trips = [] } = useTrips()
  const [params, setParams] = useSearchParams()
  const status = useQuery({
    queryKey: ['rail-status'],
    queryFn: async () => (await api.get<{ live_search: boolean }>('/rail/status')).data,
    staleTime: 60_000,
  })
  const live = status.data?.live_search ?? false

  const home = cityOnly(user?.home_town ?? '')
  const upcoming = useMemo(
    () => [...trips].filter((t) => t.end_date >= todayIso()).sort((a, b) => a.start_date.localeCompare(b.start_date)),
    [trips],
  )
  const tripId = params.get('trip') ?? ''
  const trip = trips.find((t) => t.id === tripId)
  const [direction, setDirection] = useState<'go' | 'return'>('go')

  // The journey the user is looking at, as plain city names.
  const [fromCity, setFromCity] = useState(home)
  const [toCity, setToCity] = useState('')
  const [date, setDate] = useState(todayIso())

  useEffect(() => {
    if (!trip) return
    const dest = cityOnly(trip.destination)
    if (direction === 'go') {
      setFromCity(home)
      setToCity(dest)
      setDate(trip.start_date < todayIso() ? todayIso() : trip.start_date)
    } else {
      setFromCity(dest)
      setToCity(home)
      setDate(trip.end_date < todayIso() ? todayIso() : trip.end_date)
    }
  }, [trip, direction, home])

  return (
    <div className="space-y-8">
      <BookingTabs />
      <header className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="text-sm font-medium text-indigo-700">Getting there</p>
          <h1 className="font-display mt-1 text-4xl tracking-tight sm:text-5xl">Trains</h1>
          <p className="mt-2 max-w-xl text-slate-600">
            {live
              ? 'Search live train timetables between any two stations, then book on IRCTC.'
              : 'We fill in the journey from your trip — you book on IRCTC.'}
          </p>
        </div>
      </header>

      {/* ---- fill from a trip ---- */}
      {upcoming.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
          <span className="text-sm font-medium text-slate-700">Fill from a trip</span>
          <select
            value={tripId}
            onChange={(e) => setParams(e.target.value ? { trip: e.target.value } : {})}
            className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-900 sm:flex-none"
          >
            <option value="">Choose a trip…</option>
            {upcoming.map((t) => (
              <option key={t.id} value={t.id}>
                {t.destination} · {formatDate(t.start_date)}
              </option>
            ))}
          </select>
          {trip && (
            <div className="inline-flex rounded-lg bg-slate-100 p-1 text-sm">
              {(['go', 'return'] as const).map((d) => (
                <button key={d} onClick={() => setDirection(d)} className={`rounded-md px-3 py-1 ${direction === d ? 'bg-white font-medium shadow-sm' : 'text-slate-600'}`}>
                  {d === 'go' ? 'Onward' : 'Return'}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {live ? (
        <LiveTrainSearch key={`${fromCity}|${toCity}|${date}`} fromCity={fromCity} toCity={toCity} initialDate={date} />
      ) : (
        <LinkOut
          kind="train"
          from={fromCity}
          to={toCity}
          date={date}
          setFrom={setFromCity}
          setTo={setToCity}
          setDate={setDate}
          note={
            user?.role === 'admin'
              ? 'Live train search is off. Add a free RapidAPI key as RAPIDAPI_KEY in .env and restart the backend to search trains right here.'
              : 'IRCTC doesn’t let other sites pre-fill its search, so copy these details across.'
          }
        />
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Live train search                                                  */
/* ------------------------------------------------------------------ */

function LiveTrainSearch({ fromCity, toCity, initialDate }: { fromCity: string; toCity: string; initialDate: string }) {
  const [from, setFrom] = useState<Station | null>(null)
  const [to, setTo] = useState<Station | null>(null)
  const [date, setDate] = useState(initialDate)
  const [query, setQuery] = useState<{ from: string; to: string; date: string } | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const results = useQuery({
    queryKey: ['rail-trains', query],
    queryFn: async () =>
      (await api.get<{ trains: Train[] }>('/rail/trains', { params: query! })).data.trains,
    enabled: !!query,
    staleTime: 10 * 60_000,
    retry: false,
  })

  function submit(e: FormEvent) {
    e.preventDefault()
    setFormError(null)
    if (!from || !to) return setFormError('Pick both stations from the suggestions.')
    if (from.code === to.code) return setFormError('From and To must be different stations.')
    setQuery({ from: from.code, to: to.code, date })
  }

  function swap() {
    setFrom(to)
    setTo(from)
  }

  return (
    <div className="space-y-6">
      <form onSubmit={submit} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 lg:grid-cols-[1fr_auto_1fr_12rem_auto] lg:items-end">
        <StationField label="From" seed={fromCity} value={from} onChange={setFrom} />
        <button
          type="button"
          onClick={swap}
          aria-label="Swap stations"
          className="mx-auto flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 text-slate-500 hover:bg-slate-50 lg:mb-1"
        >
          <Icon name="arrow" className="h-4 w-4 rotate-90 lg:rotate-0" />
        </button>
        <StationField label="To" seed={toCity} value={to} onChange={setTo} />
        <label className="block text-sm">
          <span className="mb-2 block font-medium text-slate-800">Date</span>
          <input
            type="date"
            min={todayIso()}
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full rounded-xl border border-slate-200 px-3.5 py-3 text-[15px] outline-none focus:border-slate-900"
          />
        </label>
        <button type="submit" className="flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-6 py-3 text-[15px] font-semibold text-white hover:bg-slate-800">
          Search trains
        </button>
        {formError && <p className="text-sm text-red-600 lg:col-span-5">{formError}</p>}
      </form>

      {results.isFetching && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => <div key={i} className="h-28 animate-pulse rounded-2xl bg-slate-200/60" />)}
        </div>
      )}
      {results.isError && (
        <p className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {apiErrorMessage(results.error, 'Train search failed. Try again in a minute.')}
        </p>
      )}
      {results.data && !results.isFetching && (
        results.data.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center text-sm text-slate-500">
            No direct trains found between these stations on {ddmmyyyy(date)}. Try a nearby station or another date.
          </p>
        ) : (
          <section className="space-y-3">
            <p className="text-sm text-slate-500">
              {results.data.length} train{results.data.length > 1 ? 's' : ''} · {from?.name} → {to?.name} · {ddmmyyyy(date)}
            </p>
            {results.data.map((t) => <TrainCard key={t.number} t={t} />)}
            <p className="text-xs text-slate-400">
              Timetables come from a third-party IRCTC data API and can occasionally be out of date. Always confirm on IRCTC before booking.
            </p>
          </section>
        )
      )}
    </div>
  )
}

function TrainCard({ t }: { t: Train }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold">
            {t.name ?? 'Train'} <span className="font-normal text-slate-400">#{t.number}</span>
          </p>
          {t.run_days.length > 0 && <p className="mt-0.5 text-xs text-slate-500">Runs {t.run_days.join(', ')}</p>}
        </div>
        {t.train_type && <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">{t.train_type}</span>}
      </div>

      <div className="mt-5 grid grid-cols-[1fr_auto_1fr] items-center gap-4">
        <div>
          <p className="text-2xl font-semibold tabular-nums">{t.departs ?? '—'}</p>
          <p className="truncate text-sm text-slate-500">{t.from_name ?? t.from_code} <span className="text-slate-400">({t.from_code})</span></p>
        </div>
        <div className="flex flex-col items-center text-xs text-slate-500">
          <span>{t.duration ? `${t.duration.replace(':', 'h ')}m` : ''}</span>
          <span className="my-1 h-px w-16 bg-slate-300 sm:w-28" />
        </div>
        <div className="text-right">
          <p className="text-2xl font-semibold tabular-nums">
            {t.arrives ?? '—'}
            {t.arrives_day_offset ? <sup className="ml-0.5 text-xs font-medium text-amber-600">+{t.arrives_day_offset}</sup> : null}
          </p>
          <p className="truncate text-sm text-slate-500">{t.to_name ?? t.to_code} <span className="text-slate-400">({t.to_code})</span></p>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
        <div className="flex flex-wrap gap-1.5">
          {t.classes.map((c) => (
            <span key={c} className="rounded-md border border-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700">{c}</span>
          ))}
        </div>
        <a
          href={IRCTC_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
        >
          Book on IRCTC <Icon name="arrow" className="h-4 w-4 -rotate-45" />
        </a>
      </div>
    </article>
  )
}

function StationField({
  label, seed, value, onChange,
}: { label: string; seed: string; value: Station | null; onChange: (s: Station | null) => void }) {
  const [text, setText] = useState(seed)
  const [open, setOpen] = useState(false)
  const [results, setResults] = useState<Station[]>([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const box = useRef<HTMLDivElement>(null)
  const skip = useRef(false)

  useEffect(() => {
    if (value) {
      skip.current = true
      setText(`${value.name} (${value.code})`)
    }
  }, [value])

  useEffect(() => {
    if (skip.current) {
      skip.current = false
      return
    }
    const q = text.replace(/\(.*\)/, '').trim()
    if (q.length < 2) {
      setResults([])
      return
    }
    let cancelled = false
    const t = setTimeout(async () => {
      setLoading(true)
      setErr(null)
      try {
        const { data } = await api.get<Station[]>('/rail/stations', { params: { q } })
        if (!cancelled) {
          setResults(data)
          setOpen(true)
        }
      } catch (e) {
        if (!cancelled) setErr(apiErrorMessage(e, 'Station search failed.'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 400)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [text])

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  return (
    <div ref={box} className="relative text-sm">
      <span className="mb-2 block font-medium text-slate-800">{label}</span>
      <span className="relative block">
        <span className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-slate-400">
          <Icon name="train" className="h-[18px] w-[18px]" />
        </span>
        <input
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            onChange(null)
          }}
          onFocus={() => results.length && setOpen(true)}
          placeholder="City or station code"
          className="w-full rounded-xl border border-slate-200 py-3 pr-10 pl-11 text-[15px] outline-none focus:border-slate-900"
        />
        {loading && <span className="absolute top-1/2 right-3.5 h-4 w-4 -translate-y-1/2 animate-spin rounded-full border-2 border-slate-200 border-t-slate-600" />}
      </span>
      {err && <span className="mt-1 block text-xs text-red-600">{err}</span>}
      {open && (
        <ul className="absolute z-30 mt-1 max-h-72 w-full overflow-auto rounded-xl border border-slate-200 bg-white py-1 shadow-xl">
          {results.length === 0 ? (
            <li className="px-4 py-3 text-slate-500">No station found.</li>
          ) : (
            results.map((s) => (
              <li key={s.code}>
                <button
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault()
                    onChange(s)
                    setOpen(false)
                  }}
                  className="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left hover:bg-slate-50"
                >
                  <span className="min-w-0">
                    <span className="block font-medium text-slate-900">{s.name}</span>
                    {s.state && <span className="block text-xs text-slate-500">{s.state}</span>}
                  </span>
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-700">{s.code}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Link-out (no live API): trains without a key, and all buses        */
/* ------------------------------------------------------------------ */

function LinkOut({
  kind, from, to, date, setFrom, setTo, setDate, note,
}: {
  kind: 'train' | 'bus'
  from: string
  to: string
  date: string
  setFrom: (v: string) => void
  setTo: (v: string) => void
  setDate: (v: string) => void
  note: string
}) {
  const [copied, setCopied] = useState<string | null>(null)
  async function copy(label: string, value: string) {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(label)
      setTimeout(() => setCopied(null), 1500)
    } catch {
      /* clipboard blocked */
    }
  }
  const input = 'w-full rounded-xl border border-slate-200 px-3.5 py-3 text-[15px] outline-none focus:border-slate-900'
  const fields = [
    { label: 'From', value: from, set: setFrom, type: 'text' },
    { label: 'To', value: to, set: setTo, type: 'text' },
    { label: 'Date', value: date, set: setDate, type: 'date' },
  ]

  return (
    <section className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="grid gap-4 sm:grid-cols-3">
        {fields.map((f) => (
          <label key={f.label} className="block text-sm">
            <span className="mb-2 flex items-center justify-between font-medium text-slate-800">
              {f.label}
              <button
                type="button"
                onClick={() => copy(f.label, f.type === 'date' ? ddmmyyyy(f.value) : f.value)}
                className="text-xs font-medium text-indigo-700 hover:underline"
              >
                {copied === f.label ? 'Copied' : 'Copy'}
              </button>
            </span>
            <input type={f.type} value={f.value} onChange={(e) => f.set(e.target.value)} className={input} />
          </label>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {kind === 'train' ? (
          <a href={IRCTC_URL} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800">
            Search on IRCTC <Icon name="arrow" className="h-4 w-4 -rotate-45" />
          </a>
        ) : (
          BUS_SITES.map((s, i) => (
            <a
              key={s.name}
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className={`inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold ${i === 0 ? 'bg-slate-950 text-white hover:bg-slate-800' : 'border border-slate-200 text-slate-800 hover:bg-slate-50'}`}
            >
              Search on {s.name} <Icon name="arrow" className="h-4 w-4 -rotate-45" />
            </a>
          ))
        )}
        <Link to="/dashboard" className="text-sm text-slate-500 hover:text-slate-900">My trips</Link>
      </div>
      <p className="rounded-xl bg-slate-50 px-4 py-3 text-xs leading-relaxed text-slate-600">{note}</p>
    </section>
  )
}
