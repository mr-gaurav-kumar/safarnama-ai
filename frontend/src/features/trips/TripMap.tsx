import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet'
import type { LatLngTuple } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { ItineraryDay } from '@/features/trips/types'

interface Stop {
  day: number
  order: number
  time: string
  place: string
  activity: string
  position: LatLngTuple
}

/**
 * The trip on a map. One day is in focus at a time: its stops in the accent
 * colour, joined in visiting order; every other day's stops sit behind in grey.
 * That keeps a 10-day trip readable -- one hue plus grey, never ten hues.
 */
export function TripMap({ days }: { days: ItineraryDay[] }) {
  const stops = useMemo<Stop[]>(
    () =>
      days.flatMap((d) =>
        d.items.flatMap((item, i) =>
          item.lat != null && item.lng != null
            ? [{
                day: d.day,
                order: i + 1,
                time: item.time,
                place: item.place,
                activity: item.activity,
                position: [item.lat, item.lng] as LatLngTuple,
              }]
            : [],
        ),
      ),
    [days],
  )

  const daysWithStops = useMemo(() => [...new Set(stops.map((s) => s.day))], [stops])
  const [focusDay, setFocusDay] = useState<number | null>(null)
  const active = focusDay ?? daysWithStops[0] ?? null

  if (stops.length === 0) {
    return (
      <section className="rounded-lg border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-500">
        No map for this plan — its places could not be located. Maps need an internet
        connection when the plan is made.
      </section>
    )
  }

  const inFocus = stops.filter((s) => s.day === active)
  const behind = stops.filter((s) => s.day !== active)

  return (
    <section className="rounded-lg border border-slate-200 bg-white">
      <header className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-5 py-3">
        <h2 className="mr-2 text-lg font-medium">Map</h2>
        {daysWithStops.map((d) => (
          <button
            key={d}
            type="button"
            aria-pressed={d === active}
            onClick={() => setFocusDay(d)}
            className={`rounded-full border px-3 py-1 text-xs ${
              d === active
                ? 'border-slate-900 bg-slate-900 text-white'
                : 'border-slate-300 text-slate-700 hover:border-slate-500'
            }`}
          >
            Day {d}
          </button>
        ))}
      </header>

      <div className="h-80 overflow-hidden rounded-b-lg">
        <MapContainer
          center={stops[0].position}
          zoom={12}
          scrollWheelZoom={false}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitTo points={stops.map((s) => s.position)} />

          {behind.map((s) => (
            <CircleMarker
              key={`b-${s.day}-${s.order}`}
              center={s.position}
              radius={5}
              pathOptions={{
                color: 'var(--viz-surface)',
                weight: 2,
                fillColor: 'var(--viz-muted-mark)',
                fillOpacity: 1,
              }}
            >
              <StopTooltip stop={s} />
            </CircleMarker>
          ))}

          {inFocus.length > 1 && (
            <Polyline
              positions={inFocus.map((s) => s.position)}
              pathOptions={{ color: 'var(--viz-domestic)', weight: 2, lineCap: 'round', lineJoin: 'round' }}
            />
          )}

          {inFocus.map((s) => (
            <CircleMarker
              key={`f-${s.day}-${s.order}`}
              center={s.position}
              radius={7}
              pathOptions={{
                color: 'var(--viz-surface)',
                weight: 2,
                fillColor: 'var(--viz-domestic)',
                fillOpacity: 1,
              }}
            >
              <StopTooltip stop={s} />
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </section>
  )
}

function StopTooltip({ stop }: { stop: Stop }) {
  return (
    <Tooltip direction="top" offset={[0, -6]}>
      <span className="block font-medium">{stop.place}</span>
      <span className="text-slate-500">
        Day {stop.day} · {stop.time} · {stop.activity}
      </span>
    </Tooltip>
  )
}

/** Frame every stop once, when the plan loads -- not on every day switch, so
 *  switching days never makes the map jump. */
function FitTo({ points }: { points: LatLngTuple[] }) {
  const map = useMap()
  const key = points.map((p) => p.join(',')).join(';')
  useEffect(() => {
    if (points.length === 1) {
      map.setView(points[0], 13)
    } else if (points.length > 1) {
      map.fitBounds(points, { padding: [28, 28], maxZoom: 14 })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, key])
  return null
}
