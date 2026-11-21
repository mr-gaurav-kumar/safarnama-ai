import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { formatDate, formatINR, useTrips } from '@/features/trips/api'
import type { Trip } from '@/features/trips/types'

/* ------------------------------------------------------------------ */
/*  Query parsing                                                      */
/*                                                                     */
/*  One box, many parameters. Examples that work:                      */
/*    goa                  destination / tag / status text             */
/*    under 30k  <30000    budget at most                              */
/*    above 50k  >50000    budget at least                             */
/*    20k-50k              budget range                                */
/*    40000                budget about this (±20%)                    */
/*    4 people             travellers                                  */
/*    december 2026        start month / year                          */
/*    completed  group     status / shared trips                       */
/* ------------------------------------------------------------------ */

const MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

interface Filters {
  words: string[]
  minBudget?: number
  maxBudget?: number
  travelers?: number
  month?: number
  year?: number
}

function amount(raw: string): number {
  const s = raw.toLowerCase().replace(/[₹,\s]/g, '')
  if (s.endsWith('k')) return Number(s.slice(0, -1)) * 1_000
  if (s.endsWith('l') || s.endsWith('lakh')) return Number(s.replace(/l(akh)?$/, '')) * 100_000
  return Number(s)
}

const NUM = String.raw`₹?\s?\d[\d,]*(?:\.\d+)?\s?(?:k|l|lakh)?`

function parse(query: string): Filters {
  let q = ` ${query.toLowerCase()} `
  const f: Filters = { words: [] }
  const take = (re: RegExp, fn: (m: RegExpMatchArray) => void) => {
    const m = q.match(re)
    if (m) {
      fn(m)
      q = q.replace(m[0], ' ')
    }
  }

  take(new RegExp(`(${NUM})\\s*(?:-|to)\\s*(${NUM})`), (m) => {
    f.minBudget = amount(m[1])
    f.maxBudget = amount(m[2])
  })
  take(new RegExp(`(?:<=?|under|below|upto|up to|less than|max|within)\\s*(${NUM})`), (m) => {
    f.maxBudget = amount(m[1])
  })
  take(new RegExp(`(?:>=?|above|over|more than|min|at least)\\s*(${NUM})`), (m) => {
    f.minBudget = amount(m[1])
  })
  take(/\b(\d{1,2})\s*(?:people|persons?|travell?ers?|pax|log|adults?)\b/, (m) => {
    f.travelers = Number(m[1])
  })
  take(/\b(20\d{2})\b/, (m) => {
    f.year = Number(m[1])
  })
  for (let i = 0; i < 12; i++) {
    take(new RegExp(`\\b${MONTHS[i]}[a-z]*\\b`), () => {
      f.month = i + 1
    })
  }
  take(new RegExp(`(?:^|\\s)(${NUM})(?=\\s|$)`), (m) => {
    const n = amount(m[1])
    if (n <= 20) f.travelers = n
    else {
      f.minBudget = n * 0.8
      f.maxBudget = n * 1.2
    }
  })

  f.words = q.split(/\s+/).filter((w) => w.length > 0 && w !== 'in' && w !== 'trip' && w !== 'trips')
  return f
}

function haystack(t: Trip): string {
  return [
    t.destination,
    t.status,
    t.plan_status,
    t.role,
    t.member_count > 1 || t.role === 'member' ? 'group shared friends' : 'solo',
    ...t.style_tags,
    formatDate(t.start_date),
    formatDate(t.end_date),
  ]
    .join(' ')
    .toLowerCase()
}

function matches(t: Trip, f: Filters): boolean {
  const budget = Number(t.budget)
  if (f.minBudget != null && budget < f.minBudget) return false
  if (f.maxBudget != null && budget > f.maxBudget) return false
  if (f.travelers != null && t.travelers !== f.travelers) return false
  const start = new Date(`${t.start_date}T00:00:00`)
  if (f.month != null && start.getMonth() + 1 !== f.month) return false
  if (f.year != null && start.getFullYear() !== f.year) return false
  const text = haystack(t)
  return f.words.every((w) => text.includes(w))
}

function describe(f: Filters): string[] {
  const out: string[] = []
  if (f.minBudget != null && f.maxBudget != null) out.push(`${formatINR(f.minBudget)} – ${formatINR(f.maxBudget)}`)
  else if (f.maxBudget != null) out.push(`≤ ${formatINR(f.maxBudget)}`)
  else if (f.minBudget != null) out.push(`≥ ${formatINR(f.minBudget)}`)
  if (f.travelers != null) out.push(`${f.travelers} travellers`)
  if (f.month != null) out.push(new Date(2000, f.month - 1).toLocaleString('en-IN', { month: 'long' }))
  if (f.year != null) out.push(String(f.year))
  f.words.forEach((w) => out.push(`"${w}"`))
  return out
}

const STATUS_STYLE: Record<string, string> = {
  completed: 'bg-emerald-100 text-emerald-700',
  processing: 'bg-amber-100 text-amber-700',
  failed: 'bg-red-100 text-red-700',
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function TripSearch() {
  const { data: trips = [], isPending } = useTrips()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)
  const boxRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const filters = useMemo(() => parse(query), [query])
  const results = useMemo(
    () => (query.trim() ? trips.filter((t) => matches(t, filters)) : trips).slice(0, 8),
    [trips, filters, query],
  )

  useEffect(() => setHighlight(0), [query])

  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false)
    }
    // Ctrl+K / "/" focuses the search from anywhere.
    function onKey(e: KeyboardEvent) {
      const typing = (e.target as HTMLElement)?.closest('input, textarea, [contenteditable]')
      if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !typing)) {
        e.preventDefault()
        inputRef.current?.focus()
        setOpen(true)
      }
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [])

  function go(trip: Trip) {
    setOpen(false)
    setQuery('')
    inputRef.current?.blur()
    navigate(`/trips/${trip.id}`)
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setHighlight((h) => Math.min(h + 1, Math.max(results.length - 1, 0)))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlight((h) => Math.max(h - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (results[highlight]) go(results[highlight])
    } else if (e.key === 'Escape') {
      setOpen(false)
      inputRef.current?.blur()
    }
  }

  const chips = query.trim() ? describe(filters) : []

  return (
    <div ref={boxRef} className="relative w-full">
      <div
        className={`group flex items-center gap-2 rounded-full border px-3.5 py-1.5 transition ${
          open
            ? 'border-indigo-400 bg-white shadow-md ring-4 ring-indigo-100'
            : 'border-slate-200 bg-slate-100/80 hover:border-slate-300 hover:bg-white'
        }`}
      >
        <SearchIcon className={`h-4 w-4 shrink-0 ${open ? 'text-indigo-500' : 'text-slate-400'}`} />
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          aria-label="Search your trips"
          className="min-w-0 flex-1 bg-transparent text-sm text-slate-900 outline-none"
        />
        {query ? (
          <button
            type="button"
            aria-label="Clear search"
            onClick={() => {
              setQuery('')
              inputRef.current?.focus()
            }}
            className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-200 text-xs text-slate-600 hover:bg-slate-300"
          >
            ×
          </button>
        ) : (
          <kbd className="hidden rounded-md border border-slate-200 bg-white px-1.5 py-0.5 font-sans text-[10px] font-medium text-slate-400 shadow-sm sm:block">
            Ctrl K
          </kbd>
        )}
      </div>

      {open && (
        <div className="absolute left-0 z-[1300] mt-2 w-[min(30rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl ring-1 ring-black/5">
          {chips.length > 0 && (
            <div className="flex flex-wrap gap-1.5 border-b border-slate-100 px-3 py-2">
              {chips.map((c) => (
                <span key={c} className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700">
                  {c}
                </span>
              ))}
            </div>
          )}

          {isPending ? (
            <p className="px-4 py-3 text-sm text-slate-500">Loading your trips…</p>
          ) : trips.length === 0 ? (
            <div className="px-4 py-4 text-sm text-slate-600">
              No trips yet.{' '}
              <Link to="/trips/new" onClick={() => setOpen(false)} className="font-medium text-indigo-600 hover:underline">
                Plan your first trip →
              </Link>
            </div>
          ) : results.length === 0 ? (
            <p className="px-4 py-3 text-sm text-slate-500">No trips match.</p>
          ) : (
            <>
              {!query.trim() && (
                <p className="px-4 pt-3 text-xs font-medium tracking-wide text-slate-400 uppercase">Recent trips</p>
              )}
              <ul className="max-h-80 overflow-auto py-1">
                {results.map((t, i) => (
                  <li key={t.id}>
                    <button
                      type="button"
                      onMouseEnter={() => setHighlight(i)}
                      onClick={() => go(t)}
                      className={`flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left ${
                        i === highlight ? 'bg-indigo-50' : ''
                      }`}
                    >
                      <span className="min-w-0">
                        <span className="flex items-center gap-2 truncate font-medium"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-indigo-100 text-xs text-indigo-700">{t.destination.trim()[0]?.toUpperCase()}</span>{t.destination}</span>
                        <span className="mt-0.5 block truncate pl-9 text-xs text-slate-500">
                          {formatDate(t.start_date)} – {formatDate(t.end_date)} · {t.travelers} traveller
                          {t.travelers > 1 ? 's' : ''}
                          {t.style_tags.length > 0 && ` · ${t.style_tags.join(', ')}`}
                        </span>
                      </span>
                      <span className="shrink-0 text-right">
                        <span className="block text-sm font-semibold">{formatINR(t.budget)}</span>
                        <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLE[t.status] ?? 'bg-slate-100 text-slate-600'}`}>
                          {t.status}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}

          <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50 px-4 py-2 text-xs">
            <span className="flex flex-wrap gap-1 text-slate-500">
              {['goa', 'under 30k', '4 people', 'dec'].map((ex) => (
                <button
                  key={ex}
                  type="button"
                  onClick={() => {
                    setQuery(ex)
                    inputRef.current?.focus()
                  }}
                  className="rounded-full border border-slate-200 bg-white px-2 py-0.5 hover:border-indigo-300 hover:text-indigo-700"
                >
                  {ex}
                </button>
              ))}
            </span>
            <Link to="/dashboard" onClick={() => setOpen(false)} className="shrink-0 font-medium text-indigo-600 hover:underline">
              All trips →
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={2} className={className} aria-hidden>
      <circle cx="9" cy="9" r="6" />
      <path d="m14 14 3.5 3.5" strokeLinecap="round" />
    </svg>
  )
}
