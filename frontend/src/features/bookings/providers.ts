/**
 * Every outside booking site the app sends people to, and how to build a
 * search link for each.
 *
 * `prefilled: true` means the link opens the site's results with the journey
 * already filled in. `false` means the site has no public search link (or its
 * links need private city ids), so we open its search page and the user
 * copies the details across from our form.
 *
 * These URL formats belong to the sites, not to us, and they change without
 * notice. If one stops pre-filling, fix its builder here -- nothing else in
 * the app needs to change. To add a site: add one entry to a list below.
 */
import { airportByCode, isIndian } from './airports'

export interface Provider<Q> {
  id: string
  name: string
  blurb: string
  prefilled: boolean
  url: (q: Q) => string
}

// ---------------------------------------------------------------- helpers

const enc = encodeURIComponent
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const parts = (iso: string) => {
  const [y, m, d] = iso.split('-')
  return { y, m, d }
}
/** 2026-12-10 -> 10/12/2026 */
export const dmySlash = (iso: string) => { const { y, m, d } = parts(iso); return `${d}/${m}/${y}` }
/** 2026-12-10 -> 10-12-2026 */
const dmyDash = (iso: string) => { const { y, m, d } = parts(iso); return `${d}-${m}-${y}` }
/** 2026-12-10 -> 10122026 */
const dmyPlain = (iso: string) => { const { y, m, d } = parts(iso); return `${d}${m}${y}` }
/** 2026-12-10 -> 261210 */
const yymmdd = (iso: string) => { const { y, m, d } = parts(iso); return `${y.slice(2)}${m}${d}` }
/** 2026-12-10 -> 10-Dec-2026 */
const dMonY = (iso: string) => { const { y, m, d } = parts(iso); return `${d}-${MONTHS[Number(m) - 1]}-${y}` }

const slug = (s: string) => s.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

export const nightsBetween = (a: string, b: string) =>
  Math.max(1, Math.round((new Date(`${b}T00:00:00`).getTime() - new Date(`${a}T00:00:00`).getTime()) / 86_400_000))

// ---------------------------------------------------------------- flights

export type Cabin = 'economy' | 'premium' | 'business'

export interface FlightQuery {
  from: string // IATA code
  to: string
  depart: string // yyyy-mm-dd
  ret: string | null // null = one way
  adults: number
  cabin: Cabin
}

const isIntl = (q: FlightQuery) => !(isIndian(airportByCode(q.from)) && isIndian(airportByCode(q.to)))

const CABIN_TEXT: Record<Cabin, string> = { economy: 'economy', premium: 'premium economy', business: 'business class' }

export const FLIGHT_PROVIDERS: Provider<FlightQuery>[] = [
  {
    id: 'google',
    name: 'Google Flights',
    blurb: 'Compares most airlines and agents; good for spotting the cheapest day.',
    prefilled: true,
    url: (q) => {
      const text =
        `Flights from ${q.from} to ${q.to} on ${q.depart}` +
        (q.ret ? ` returning ${q.ret}` : ' one way') +
        ` for ${q.adults} adult${q.adults > 1 ? 's' : ''} ${CABIN_TEXT[q.cabin]}`
      return `https://www.google.com/travel/flights?q=${enc(text)}&curr=INR&hl=en-IN`
    },
  },
  {
    id: 'skyscanner',
    name: 'Skyscanner',
    blurb: 'Metasearch across airlines and agents worldwide.',
    prefilled: true,
    url: (q) => {
      const cabin = { economy: 'economy', premium: 'premiumeconomy', business: 'business' }[q.cabin]
      const path = `${q.from.toLowerCase()}/${q.to.toLowerCase()}/${yymmdd(q.depart)}/${q.ret ? `${yymmdd(q.ret)}/` : ''}`
      return `https://www.skyscanner.co.in/transport/flights/${path}?adultsv2=${q.adults}&cabinclass=${cabin}&rtn=${q.ret ? 1 : 0}`
    },
  },
  {
    id: 'makemytrip',
    name: 'MakeMyTrip',
    blurb: 'India’s largest OTA; frequent bank-card offers.',
    prefilled: true,
    url: (q) => {
      const legs = [`${q.from}-${q.to}-${dmySlash(q.depart)}`]
      if (q.ret) legs.push(`${q.to}-${q.from}-${dmySlash(q.ret)}`)
      const cabin = { economy: 'E', premium: 'PE', business: 'B' }[q.cabin]
      return (
        `https://www.makemytrip.com/flight/search?itinerary=${legs.join('_')}` +
        `&tripType=${q.ret ? 'R' : 'O'}&paxType=A-${q.adults}_C-0_I-0&intl=${isIntl(q)}&cabinClass=${cabin}&lang=eng`
      )
    },
  },
  {
    id: 'ixigo',
    name: 'ixigo',
    blurb: 'Low convenience fees; shows fare trends.',
    prefilled: true,
    url: (q) => {
      const cls = q.cabin === 'business' ? 'b' : 'e'
      return (
        `https://www.ixigo.com/search/result/flight?from=${q.from}&to=${q.to}&date=${dmyPlain(q.depart)}` +
        `&returnDate=${q.ret ? dmyPlain(q.ret) : ''}&adults=${q.adults}&children=0&infants=0&class=${cls}&source=Search%20Form`
      )
    },
  },
  {
    id: 'cleartrip',
    name: 'Cleartrip',
    blurb: 'Clean checkout; often cheaper on domestic routes.',
    prefilled: true,
    url: (q) => {
      const cls = { economy: 'Economy', premium: 'Premium%20Economy', business: 'Business' }[q.cabin]
      return (
        `https://www.cleartrip.com/flights/results?adults=${q.adults}&childs=0&infants=0&class=${cls}` +
        `&depart_date=${dmySlash(q.depart)}${q.ret ? `&return_date=${dmySlash(q.ret)}` : ''}` +
        `&from=${q.from}&to=${q.to}&intl=${isIntl(q) ? 'y' : 'n'}`
      )
    },
  },
  {
    id: 'easemytrip',
    name: 'EaseMyTrip',
    blurb: 'Zero convenience fee on many fares.',
    prefilled: false,
    url: () => 'https://www.easemytrip.com/flights.html',
  },
]

// ---------------------------------------------------------------- hotels

export interface HotelQuery {
  city: string
  checkin: string
  checkout: string
  adults: number
  rooms: number
}

export const HOTEL_PROVIDERS: Provider<HotelQuery>[] = [
  {
    id: 'booking',
    name: 'Booking.com',
    blurb: 'Huge choice, many with free cancellation.',
    prefilled: true,
    url: (q) =>
      `https://www.booking.com/searchresults.en-gb.html?ss=${enc(q.city)}&checkin=${q.checkin}&checkout=${q.checkout}` +
      `&group_adults=${q.adults}&no_rooms=${q.rooms}&group_children=0&selected_currency=INR`,
  },
  {
    id: 'google',
    name: 'Google Hotels',
    blurb: 'Compares prices from every booking site at once.',
    prefilled: true,
    url: (q) => `https://www.google.com/travel/search?q=${enc(`hotels in ${q.city}`)}&hl=en-IN&curr=INR`,
  },
  {
    id: 'agoda',
    name: 'Agoda',
    blurb: 'Strong in India and South-East Asia; good member prices.',
    prefilled: true,
    url: (q) =>
      `https://www.agoda.com/search?textToSearch=${enc(q.city)}&checkIn=${q.checkin}` +
      `&los=${nightsBetween(q.checkin, q.checkout)}&rooms=${q.rooms}&adults=${q.adults}&children=0&currency=INR`,
  },
  {
    id: 'airbnb',
    name: 'Airbnb',
    blurb: 'Homestays, cottages and whole homes — great for groups.',
    prefilled: true,
    url: (q) =>
      `https://www.airbnb.co.in/s/${enc(q.city)}/homes?checkin=${q.checkin}&checkout=${q.checkout}&adults=${q.adults}`,
  },
  {
    id: 'expedia',
    name: 'Expedia',
    blurb: 'Hotels worldwide; bundles with flights.',
    prefilled: true,
    url: (q) =>
      `https://www.expedia.co.in/Hotel-Search?destination=${enc(q.city)}&startDate=${q.checkin}&endDate=${q.checkout}` +
      `&adults=${q.adults}&rooms=${q.rooms}`,
  },
  {
    id: 'makemytrip',
    name: 'MakeMyTrip',
    blurb: 'Big Indian hotel inventory with OTA offers.',
    prefilled: false,
    url: () => 'https://www.makemytrip.com/hotels/',
  },
  {
    id: 'goibibo',
    name: 'Goibibo',
    blurb: 'Budget stays and frequent cashback.',
    prefilled: false,
    url: () => 'https://www.goibibo.com/hotels/',
  },
]

// ---------------------------------------------------------------- buses

export interface BusQuery {
  from: string // city name
  to: string
  date: string
}

export const BUS_PROVIDERS: Provider<BusQuery>[] = [
  {
    id: 'redbus',
    name: 'redBus',
    blurb: 'Most private and state (RTC) operators in one place.',
    prefilled: true,
    url: (q) =>
      `https://www.redbus.in/bus-tickets/${slug(q.from)}-to-${slug(q.to)}` +
      `?fromCityName=${enc(q.from)}&toCityName=${enc(q.to)}&onward=${dMonY(q.date)}`,
  },
  {
    id: 'makemytrip',
    name: 'MakeMyTrip Bus',
    blurb: 'Buses with MakeMyTrip offers and wallet.',
    prefilled: true,
    url: (q) => `https://www.makemytrip.com/bus/search/${enc(q.from)}/${enc(q.to)}/${dmyDash(q.date)}`,
  },
  {
    id: 'abhibus',
    name: 'AbhiBus',
    blurb: 'Strong in the south; many RTC buses.',
    prefilled: false,
    url: () => 'https://www.abhibus.com/',
  },
  {
    id: 'ixigo',
    name: 'ixigo Bus',
    blurb: 'Compare operators and fares.',
    prefilled: false,
    url: () => 'https://bus.ixigo.com/',
  },
  {
    id: 'zingbus',
    name: 'zingbus',
    blurb: 'Branded intercity sleeper buses, North India.',
    prefilled: false,
    url: () => 'https://www.zingbus.com/',
  },
  {
    id: 'intrcity',
    name: 'IntrCity SmartBus',
    blurb: 'Branded buses with tracking and clean washrooms.',
    prefilled: false,
    url: () => 'https://www.intrcity.com/',
  },
]
