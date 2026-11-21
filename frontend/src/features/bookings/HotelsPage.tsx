import { useEffect, useState } from 'react'
import { CityField } from '@/components/CityField'
import { HOTEL_PROVIDERS, dmySlash, nightsBetween, type HotelQuery } from './providers'
import {
  BookingHeader, NumberField, ProviderList, TripPicker,
  addDays, cityOnly, inputCls, notPast, todayIso, useTripPrefill,
} from './shared'

/**
 * Hotels and stays: one search, opened on Booking.com, Agoda, Airbnb and
 * others. A trip fills in the destination, check-in/out and guests.
 */
export function HotelsPage() {
  const { trip, tripId, setTripId, upcoming } = useTripPrefill()

  const [city, setCity] = useState('')
  const [checkin, setCheckin] = useState(addDays(todayIso(), 7))
  const [checkout, setCheckout] = useState(addDays(todayIso(), 9))
  const [adults, setAdults] = useState(2)
  const [rooms, setRooms] = useState(1)

  useEffect(() => {
    if (!trip) return
    const start = notPast(trip.start_date)
    // You leave on the last day of the trip; a one-day trip still needs a night.
    const end = trip.end_date > start ? trip.end_date : addDays(start, 1)
    setCity(trip.destination)
    setCheckin(start)
    setCheckout(end)
    setAdults(Math.min(16, Math.max(1, trip.travelers)))
    setRooms(Math.max(1, Math.ceil(trip.travelers / 2)))
  }, [trip])

  const place = city.trim()
  let problem: string | null = null
  if (cityOnly(place).length < 2) problem = 'Where are you staying? Pick a city.'
  else if (checkout <= checkin) problem = 'Check-out must be after check-in.'
  else if (rooms > adults) problem = 'Each room needs at least one adult.'

  const query: HotelQuery | null = place ? { city: place, checkin, checkout, adults, rooms } : null
  const nights = nightsBetween(checkin, checkout)

  const details = [
    { label: 'Where', value: cityOnly(place) },
    { label: 'Check-in', value: dmySlash(checkin) },
    { label: 'Check-out', value: dmySlash(checkout) },
    { label: 'Guests', value: `${adults} adult${adults > 1 ? 's' : ''}, ${rooms} room${rooms > 1 ? 's' : ''}` },
  ]

  return (
    <div className="space-y-8">
      <BookingHeader
        eyebrow="Where to stay"
        title="Hotels & stays"
        subtitle="Hotels, homestays and hostels. Compare the same dates on several sites — each opens in a new tab, and you book there."
      />

      <TripPicker upcoming={upcoming} tripId={tripId} setTripId={setTripId} />

      <section className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <CityField label="City or area" value={city} onChange={setCity} required={false} />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="block text-sm">
            <span className="mb-2 block font-medium text-slate-800">Check-in</span>
            <input
              type="date"
              min={todayIso()}
              value={checkin}
              onChange={(e) => {
                setCheckin(e.target.value)
                if (checkout <= e.target.value) setCheckout(addDays(e.target.value, 1))
              }}
              className={inputCls}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-2 flex justify-between font-medium text-slate-800">
              Check-out
              {checkout > checkin && <span className="font-normal text-slate-500">{nights} night{nights > 1 ? 's' : ''}</span>}
            </span>
            <input type="date" min={addDays(checkin, 1)} value={checkout} onChange={(e) => setCheckout(e.target.value)} className={inputCls} />
          </label>
          <NumberField label="Adults" value={adults} onChange={setAdults} max={16} />
          <NumberField label="Rooms" value={rooms} onChange={setRooms} max={8} />
        </div>
      </section>

      <ProviderList providers={HOTEL_PROVIDERS} query={query} details={details} problem={problem} />
    </div>
  )
}
