import { useEffect, useState } from 'react'
import { Icon } from '@/components/Icon'
import { CityField } from '@/components/CityField'
import { BUS_PROVIDERS, dmySlash, type BusQuery } from './providers'
import {
  BookingHeader, DirectionToggle, ProviderList, TripPicker,
  addDays, cityOnly, inputCls, notPast, todayIso, useTripPrefill,
} from './shared'

/**
 * Buses: there is no public bus-booking API in India (redBus and AbhiBus only
 * open theirs to B2B partners), so this fills in the route and opens it on
 * redBus, MakeMyTrip and the rest.
 */
export function BusesPage() {
  const { trip, tripId, setTripId, upcoming, home } = useTripPrefill()
  const [direction, setDirection] = useState<'go' | 'return'>('go')
  const [from, setFrom] = useState(home)
  const [to, setTo] = useState('')
  const [date, setDate] = useState(addDays(todayIso(), 1))

  useEffect(() => {
    if (!trip) return
    if (direction === 'go') {
      setFrom(home)
      setTo(trip.destination)
      setDate(notPast(trip.start_date))
    } else {
      setFrom(trip.destination)
      setTo(home)
      setDate(notPast(trip.end_date))
    }
  }, [trip, direction, home])

  const a = cityOnly(from)
  const b = cityOnly(to)
  let problem: string | null = null
  if (a.length < 2) problem = 'Where does the bus start? Pick a city in “From”.'
  else if (b.length < 2) problem = 'Where are you going? Pick a city in “To”.'
  else if (a.toLowerCase() === b.toLowerCase()) problem = 'From and To must be different cities.'

  const query: BusQuery | null = a && b ? { from: a, to: b, date } : null
  const details = [
    { label: 'From', value: a },
    { label: 'To', value: b },
    { label: 'Date', value: dmySlash(date) },
  ]

  return (
    <div className="space-y-8">
      <BookingHeader
        eyebrow="Getting there"
        title="Buses"
        subtitle="Sleeper, Volvo and state (RTC) buses. We fill in the route and open it on redBus, MakeMyTrip and others — you book there."
      />

      <TripPicker upcoming={upcoming} tripId={tripId} setTripId={setTripId}>
        {trip && <DirectionToggle value={direction} onChange={setDirection} />}
      </TripPicker>

      <section className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 lg:grid-cols-[1fr_auto_1fr_12rem] lg:items-end">
        <CityField label="From" value={from} onChange={setFrom} required={false} />
        <button
          type="button"
          onClick={() => { setFrom(to); setTo(from) }}
          aria-label="Swap cities"
          className="mx-auto flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 text-slate-500 hover:bg-slate-50 lg:mb-1"
        >
          <Icon name="arrow" className="h-4 w-4 rotate-90 lg:rotate-0" />
        </button>
        <CityField label="To" value={to} onChange={setTo} required={false} />
        <label className="block text-sm">
          <span className="mb-2 block font-medium text-slate-800">Date</span>
          <input type="date" min={todayIso()} value={date} onChange={(e) => setDate(e.target.value)} className={inputCls} />
        </label>
      </section>

      <ProviderList providers={BUS_PROVIDERS} query={query} details={details} problem={problem} />
    </div>
  )
}
