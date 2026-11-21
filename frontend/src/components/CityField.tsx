import { useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'
import { Field } from '@/features/auth/AuthLayout'
import { Icon } from '@/components/Icon'

interface City {
  name: string
  state: string
  label: string
}

/** "City, State" -- what every city picker stores. */
export const isPickedCity = (v: string) => /^[^,]+,\s*[^,]+$/.test(v.trim())

/**
 * Indian city picker. Type a couple of letters and it suggests
 * "City, State" from the built-in list (and a map search for rarer towns).
 * Arrow keys + Enter work; the chosen value is stored as "City, State".
 */
export function CityField({
  label,
  value,
  onChange,
  hint,
  required = true,
  optional,
  error,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  hint?: string
  required?: boolean
  optional?: boolean
  error?: string
}) {
  const [results, setResults] = useState<City[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [active, setActive] = useState(0)
  const skip = useRef(false)
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (skip.current) {
      skip.current = false
      return
    }
    const q = value.split(',')[0].trim()
    if (q.length < 2) {
      setResults([])
      setOpen(false)
      return
    }
    let cancelled = false
    const t = setTimeout(async () => {
      setLoading(true)
      try {
        const { data } = await api.get<City[]>('/geo/cities', { params: { q, limit: 8 } })
        if (!cancelled) {
          setResults(data)
          setActive(0)
          setOpen(true)
        }
      } catch {
        if (!cancelled) setResults([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [value])

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  function pick(c: City) {
    skip.current = true
    onChange(c.label)
    setOpen(false)
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open || results.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((a) => (a + 1) % results.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => (a - 1 + results.length) % results.length)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      pick(results[active])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div ref={box} className="relative" onKeyDown={onKeyDown}>
      <Field
        label={label}
        type="text"
        icon="pin"
        value={value}
        onChange={onChange}
        autoComplete="off"
        required={required}
        optional={optional}
        error={error}
        hint={hint ?? 'Start typing — e.g. “gha” for Ghaziabad, Uttar Pradesh'}
      />
      {loading && (
        <span className="pointer-events-none absolute top-[42px] right-4 h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-slate-600" />
      )}
      {open && (
        <ul
          role="listbox"
          className="absolute z-30 mt-1 max-h-72 w-full overflow-auto rounded-xl border border-slate-200 bg-white py-1 shadow-xl ring-1 ring-black/5"
        >
          {results.length === 0 ? (
            <li className="px-4 py-3 text-sm text-slate-500">No city found — check the spelling.</li>
          ) : (
            results.map((c, i) => (
              <li key={c.label} role="option" aria-selected={i === active}>
                <button
                  type="button"
                  onMouseEnter={() => setActive(i)}
                  onMouseDown={(e) => {
                    e.preventDefault()
                    pick(c)
                  }}
                  className={`flex w-full items-center gap-3 px-4 py-2.5 text-left ${i === active ? 'bg-slate-50' : ''}`}
                >
                  <Icon name="pin" className="h-4 w-4 shrink-0 text-slate-400" />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-slate-900">{c.name}</span>
                    <span className="block text-xs text-slate-500">{c.state}</span>
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}
