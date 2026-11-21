import { useEffect, useRef, useState } from 'react'
import { Icon } from '@/components/Icon'
import { airportByCode, airportForPlace, airportLabel, searchAirports, type Airport } from './airports'
import { FLIGHT_PROVIDERS, dmySlash, type Cabin, type FlightQuery } from './providers'
import {
  BookingHeader, DirectionToggle, NumberField, ProviderList, TripPicker,
  inputCls, notPast, todayIso, useTripPrefill, addDays,
} from './shared'

/**
 * Flights: pick airports and dates once, then open the same search on Google
 * Flights, Skyscanner, MakeMyTrip and others. A trip fills it in -- home town
 * to the nearest airport of the destination (Manali -> Bhuntar KUU).
 */
export function FlightsPage() {
  const { trip, tripId, setTripId, upcoming, home } = useTripPrefill()
  const [direction, setDirection] = useState<'go' | 'return'>('go')

  const [from, setFrom] = useState<Airport | null>(() => airportForPlace(home) ?? null)
  const [to, setTo] = useState<Airport | null>(null)
  const [depart, setDepart] = useState(addDays(todayIso(), 7))
  const [roundTrip, setRoundTrip] = useState(true)
  const [ret, setRet] = useState(addDays(todayIso(), 10))
  const [adults, setAdults] = useState(1)
  const [cabin, setCabin] = useState<Cabin>('economy')
  const [noAirport, setNoAirport] = useState<string | null>(null)

  useEffect(() => {
    if (!trip) return
    const homeAp = airportForPlace(home) ?? null
    const destAp = airportForPlace(trip.destination) ?? null
    setNoAirport(destAp ? null : trip.destination.split(',')[0])
    setAdults(Math.min(9, Math.max(1, trip.travelers)))
    if (direction === 'go') {
      setFrom(homeAp)
      setTo(destAp)
      setDepart(notPast(trip.start_date))
      setRoundTrip(true)
      setRet(notPast(trip.end_date))
    } else {
      setFrom(destAp)
      setTo(homeAp)
      setDepart(notPast(trip.end_date))
      setRoundTrip(false)
    }
  }, [trip, direction, home])

  let problem: string | null = null
  if (!from) problem = 'Pick the airport you are flying from.'
  else if (!to) problem = noAirport ? `We don’t know the nearest airport to ${noAirport} yet — pick one in “To”.` : 'Pick the airport you are flying to.'
  else if (from.code === to.code) problem = 'From and To must be different airports.'
  else if (roundTrip && ret < depart) problem = 'The return date is before the departure date.'

  const query: FlightQuery | null =
    from && to ? { from: from.code, to: to.code, depart, ret: roundTrip ? ret : null, adults, cabin } : null

  const details = query
    ? [
        { label: 'From', value: airportLabel(from!) },
        { label: 'To', value: airportLabel(to!) },
        { label: 'Depart', value: dmySlash(depart) },
        ...(roundTrip ? [{ label: 'Return', value: dmySlash(ret) }] : []),
        { label: 'Adults', value: String(adults) },
      ]
    : []

  return (
    <div className="space-y-8">
      <BookingHeader
        eyebrow="Getting there"
        title="Flights"
        subtitle="Search once, compare on several sites. Each one opens in a new tab with your journey filled in — you book and pay there."
      />

      <TripPicker upcoming={upcoming} tripId={tripId} setTripId={setTripId}>
        {trip && <DirectionToggle value={direction} onChange={setDirection} />}
      </TripPicker>

      <section className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="inline-flex rounded-lg bg-slate-100 p-1 text-sm">
          {[true, false].map((rt) => (
            <button
              key={String(rt)}
              type="button"
              onClick={() => setRoundTrip(rt)}
              className={`rounded-md px-3 py-1 ${roundTrip === rt ? 'bg-white font-medium shadow-sm' : 'text-slate-600'}`}
            >
              {rt ? 'Round trip' : 'One way'}
            </button>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr] lg:items-end">
          <AirportField label="From" value={from} onChange={setFrom} />
          <button
            type="button"
            onClick={() => { setFrom(to); setTo(from) }}
            aria-label="Swap airports"
            className="mx-auto flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 text-slate-500 hover:bg-slate-50 lg:mb-1"
          >
            <Icon name="arrow" className="h-4 w-4 rotate-90 lg:rotate-0" />
          </button>
          <AirportField label="To" value={to} onChange={setTo} />
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="block text-sm">
            <span className="mb-2 block font-medium text-slate-800">Depart</span>
            <input type="date" min={todayIso()} value={depart} onChange={(e) => setDepart(e.target.value)} className={inputCls} />
          </label>
          <label className="block text-sm">
            <span className="mb-2 block font-medium text-slate-800">Return</span>
            <input
              type="date"
              min={depart}
              value={ret}
              disabled={!roundTrip}
              onChange={(e) => setRet(e.target.value)}
              className={`${inputCls} disabled:bg-slate-50 disabled:text-slate-400`}
            />
          </label>
          <NumberField label="Adults" value={adults} onChange={setAdults} />
          <label className="block text-sm">
            <span className="mb-2 block font-medium text-slate-800">Class</span>
            <select value={cabin} onChange={(e) => setCabin(e.target.value as Cabin)} className={`${inputCls} bg-white`}>
              <option value="economy">Economy</option>
              <option value="premium">Premium economy</option>
              <option value="business">Business</option>
            </select>
          </label>
        </div>
      </section>

      <ProviderList providers={FLIGHT_PROVIDERS} query={query} details={details} problem={problem} />
    </div>
  )
}

/** Type a city, an airport or a code; pick from the built-in airport list. */
function AirportField({ label, value, onChange }: { label: string; value: Airport | null; onChange: (a: Airport | null) => void }) {
  const [text, setText] = useState(value ? airportLabel(value) : '')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const box = useRef<HTMLDivElement>(null)
  const results = open ? searchAirports(text) : []

  // Follow changes made from outside (trip prefill, swap). Clearing only
  // wipes a picked label like "Delhi (DEL)" -- never what the user is typing.
  useEffect(() => {
    if (value) setText(airportLabel(value))
    else setText((t) => (/\([A-Z]{3}\)$/.test(t) ? '' : t))
  }, [value])

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  function pick(a: Airport) {
    onChange(a)
    setText(airportLabel(a))
    setOpen(false)
  }

  return (
    <div ref={box} className="relative text-sm">
      <span className="mb-2 block font-medium text-slate-800">{label}</span>
      <input
        value={text}
        onChange={(e) => {
          setText(e.target.value)
          setActive(0)
          setOpen(true)
          // A bare 3-letter code the list knows counts as picked.
          const exact = e.target.value.trim().length === 3 ? airportByCode(e.target.value.trim()) : undefined
          onChange(exact ?? null)
        }}
        onFocus={() => text && setOpen(true)}
        onKeyDown={(e) => {
          if (!results.length) return
          if (e.key === 'ArrowDown') { e.preventDefault(); setActive((i) => Math.min(i + 1, results.length - 1)) }
          if (e.key === 'ArrowUp') { e.preventDefault(); setActive((i) => Math.max(i - 1, 0)) }
          if (e.key === 'Enter') { e.preventDefault(); pick(results[active]) }
        }}
        placeholder="City or airport code"
        className={inputCls}
      />
      {open && text.trim().length >= 2 && !value && (
        <ul className="absolute z-30 mt-1 max-h-72 w-full overflow-auto rounded-xl border border-slate-200 bg-white py-1 shadow-xl">
          {results.length === 0 ? (
            <li className="px-4 py-3 text-slate-500">No airport found. Try the nearest big city.</li>
          ) : (
            results.map((a, i) => (
              <li key={a.code}>
                <button
                  type="button"
                  onMouseDown={(e) => { e.preventDefault(); pick(a) }}
                  className={`flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left ${i === active ? 'bg-slate-50' : ''}`}
                >
                  <span className="min-w-0">
                    <span className="block font-medium text-slate-900">{a.city}</span>
                    <span className="block truncate text-xs text-slate-500">{a.name}{a.country ? `, ${a.country}` : ''}</span>
                  </span>
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-700">{a.code}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}
