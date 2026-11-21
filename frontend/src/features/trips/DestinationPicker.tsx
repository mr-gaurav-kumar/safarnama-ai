import { useEffect, useRef, useState } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import type { LatLngTuple } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { api } from '@/lib/api'
import { apiErrorMessage } from '@/lib/auth'

export interface Place {
  name: string
  label: string
  lat: number
  lng: number
  kind: string
}

/** An instant suggestion: travel destinations have coordinates, plain city names may not. */
type Suggestion = Omit<Place, 'lat' | 'lng'> & { lat: number | null; lng: number | null }

const INDIA_CENTER: LatLngTuple = [22.5, 79]
const DEBOUNCE_MS = 450

/**
 * Destination field with live place search and a map.
 * Type to search, pick a result (or click anywhere on the map) and the map
 * flies there; the chosen name is what the trip is planned for.
 */
export function DestinationPicker({
  value,
  onChange,
}: {
  value: string
  onChange: (destination: string) => void
}) {
  const [results, setResults] = useState<Place[]>([])
  const [quick, setQuick] = useState<Suggestion[]>([])
  const [open, setOpen] = useState(false)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Place | null>(null)
  const [highlight, setHighlight] = useState(0)
  const skipNextSearch = useRef(false)
  const skipQuick = useRef(false)
  const boxRef = useRef<HTMLDivElement>(null)

  // Instant, offline suggestions on every keystroke: "Naini" -> Nainital.
  useEffect(() => {
    const q = value.trim()
    if (skipQuick.current || !q) {
      skipQuick.current = false
      setQuick([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        const { data } = await api.get<Suggestion[]>('/geo/suggest', { params: { q, limit: 6 } })
        setQuick(data)
        setHighlight(0)
        if (data.length) setOpen(true)
      } catch {
        setQuick([])
      }
    }, 120)
    return () => clearTimeout(timer)
  }, [value])

  // The slower map search, for places the built-in lists do not know.
  useEffect(() => {
    if (skipNextSearch.current) {
      skipNextSearch.current = false
      return
    }
    const q = value.trim()
    if (q.length < 2) {
      setResults([])
      return
    }
    const timer = setTimeout(async () => {
      setSearching(true)
      setError(null)
      try {
        const { data } = await api.get<Place[]>('/geo/search', { params: { q } })
        setResults(data)
        setHighlight(0)
        setOpen(true)
      } catch (err) {
        setError(apiErrorMessage(err, 'Search failed.'))
      } finally {
        setSearching(false)
      }
    }, DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [value])

  // Close the dropdown on an outside click.
  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [])

  const shown: Suggestion[] = [
    ...quick,
    ...results.filter((r) => !quick.some((q) => q.name.toLowerCase() === r.name.toLowerCase())),
  ].slice(0, 10)

  async function choose(place: Suggestion) {
    skipNextSearch.current = true
    skipQuick.current = true
    onChange(place.name)
    setOpen(false)
    setQuick([])
    if (place.lat != null && place.lng != null) {
      setSelected({ ...place, lat: place.lat, lng: place.lng })
      return
    }
    // A city from the built-in list: find it on the map so the pin can drop.
    try {
      const { data } = await api.get<Place[]>('/geo/search', { params: { q: place.label, limit: 1 } })
      setSelected(data[0] ? { ...data[0], name: place.name, label: place.label } : null)
    } catch {
      setSelected(null)
    }
  }

  async function pickOnMap(lat: number, lng: number) {
    setError(null)
    try {
      const { data } = await api.get<Place | null>('/geo/reverse', { params: { lat, lng } })
      if (data) choose(data)
      else setError('No named place there — try clicking closer to a town or city.')
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not look up that point.'))
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || shown.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlight((h) => (h + 1) % shown.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlight((h) => (h - 1 + shown.length) % shown.length)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      void choose(shown[Math.min(highlight, shown.length - 1)])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className="space-y-3">
      <div ref={boxRef} className="relative">
        <span className="mb-1 block text-sm font-medium text-slate-700">Destination</span>
        <div className="relative">
          <span className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-400">
            🔍
          </span>
          <input
            required
            value={value}
            onChange={(e) => {
              onChange(e.target.value)
              setSelected(null)
            }}
            onFocus={() => shown.length > 0 && setOpen(true)}
            onKeyDown={onKeyDown}
            placeholder="Search a city or place — Goa, Jaipur, Manali…"
            autoComplete="off"
            role="combobox"
            aria-expanded={open}
            aria-controls="destination-results"
            className="w-full rounded border border-slate-300 py-2 pr-20 pl-9 text-sm outline-none focus:border-indigo-500"
          />
          {searching && (
            <span className="absolute top-1/2 right-3 -translate-y-1/2 text-xs text-slate-400">
              searching…
            </span>
          )}
        </div>

        {open && shown.length > 0 && (
          <ul
            id="destination-results"
            role="listbox"
            className="absolute z-[1000] mt-1 max-h-72 w-full overflow-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg"
          >
            {shown.map((p, i) => (
              <li
                key={`${p.name}|${p.label}`}
                role="option"
                aria-selected={i === highlight}
                onMouseEnter={() => setHighlight(i)}
                onMouseDown={(e) => {
                  e.preventDefault()
                  void choose(p)
                }}
                className={`cursor-pointer px-3 py-2 text-sm ${i === highlight ? 'bg-slate-100' : ''}`}
              >
                <p className="font-medium">📍 {p.name}</p>
                <p className="truncate text-xs text-slate-500">{p.label}</p>
              </li>
            ))}
          </ul>
        )}
        {open && !searching && shown.length === 0 && value.trim().length >= 2 && (
          <p className="absolute z-[1000] mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-500 shadow-lg">
            No places found.
          </p>
        )}
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200">
        <MapContainer
          center={INDIA_CENTER}
          zoom={4}
          scrollWheelZoom
          className="h-72 w-full"
          style={{ zIndex: 0 }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ClickToPick onPick={pickOnMap} />
          <FlyTo place={selected} />
          {results
            .filter((p) => p !== selected)
            .map((p) => (
              <CircleMarker
                key={`${p.lat},${p.lng}`}
                center={[p.lat, p.lng]}
                radius={6}
                pathOptions={{ color: '#64748b', fillColor: '#94a3b8', fillOpacity: 0.8, weight: 1 }}
                eventHandlers={{ click: () => choose(p) }}
              >
                <Tooltip>{p.name}</Tooltip>
              </CircleMarker>
            ))}
          {selected && (
            <CircleMarker
              center={[selected.lat, selected.lng]}
              radius={10}
              pathOptions={{ color: '#4338ca', fillColor: '#6366f1', fillOpacity: 0.9, weight: 2 }}
            >
              <Tooltip permanent direction="top" offset={[0, -8]}>
                {selected.name}
              </Tooltip>
            </CircleMarker>
          )}
        </MapContainer>
        <p className="border-t border-slate-100 bg-slate-50 px-3 py-1.5 text-xs text-slate-500">
          {selected
            ? `Selected: ${selected.label}`
            : 'Search above, or click anywhere on the map to pick a place.'}
        </p>
      </div>

      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}

function ClickToPick({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({ click: (e) => onPick(e.latlng.lat, e.latlng.lng) })
  return null
}

function FlyTo({ place }: { place: Place | null }) {
  const map = useMap()
  useEffect(() => {
    if (place) map.flyTo([place.lat, place.lng], 10, { duration: 1.2 })
  }, [place, map])
  return null
}
