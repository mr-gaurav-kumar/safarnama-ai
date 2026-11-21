import { useState } from 'react'
import { Button, ErrorNote } from './ui'

const TAGS = ['adventure', 'relax', 'culture', 'food', 'nature'] as const

export interface TripFormValues {
  destination: string
  start_date: string
  end_date: string
  budget: number
  travelers: number
  style_tags: string[]
}

function today(offset = 0): string {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  return d.toISOString().slice(0, 10)
}

export const EMPTY_TRIP: TripFormValues = {
  destination: '', start_date: today(7), end_date: today(9), budget: 25000, travelers: 2, style_tags: [],
}

/** Create or edit a trip's details from the admin panel. */
export function TripForm({
  initial,
  submitLabel,
  busy,
  error,
  onSubmit,
  onCancel,
  note,
}: {
  initial: TripFormValues
  submitLabel: string
  busy: boolean
  error: unknown
  onSubmit: (v: TripFormValues) => void
  onCancel: () => void
  note?: string
}) {
  const [v, setV] = useState(initial)
  const [local, setLocal] = useState<string | null>(null)
  const input = 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-900'

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        setLocal(null)
        if (v.destination.trim().length < 2) return setLocal('Enter a destination.')
        if (v.end_date < v.start_date) return setLocal('End date must not be before start date.')
        onSubmit({ ...v, destination: v.destination.trim() })
      }}
      className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/60 p-4 text-sm"
    >
      {note && <p className="text-xs text-slate-500">{note}</p>}
      <label className="block space-y-1">
        <span className="text-xs text-slate-500">Destination</span>
        <input className={input} value={v.destination} onChange={(e) => setV({ ...v, destination: e.target.value })} />
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="space-y-1">
          <span className="text-xs text-slate-500">Start date</span>
          <input type="date" className={input} value={v.start_date} onChange={(e) => setV({ ...v, start_date: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-xs text-slate-500">End date</span>
          <input type="date" className={input} min={v.start_date} value={v.end_date} onChange={(e) => setV({ ...v, end_date: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-xs text-slate-500">Budget (₹)</span>
          <input type="number" min={1000} className={input} value={v.budget || ''} onChange={(e) => setV({ ...v, budget: Number(e.target.value) })} />
        </label>
        <label className="space-y-1">
          <span className="text-xs text-slate-500">Travellers</span>
          <input type="number" min={1} max={20} className={input} value={v.travelers} onChange={(e) => setV({ ...v, travelers: Number(e.target.value) })} />
        </label>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {TAGS.map((t) => {
          const on = v.style_tags.includes(t)
          return (
            <button
              key={t}
              type="button"
              onClick={() => setV({ ...v, style_tags: on ? v.style_tags.filter((x) => x !== t) : [...v.style_tags, t] })}
              className={`rounded-full border px-3 py-1 text-xs capitalize ${on ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-600'}`}
            >
              {t}
            </button>
          )
        })}
      </div>
      {local && <p className="text-xs text-red-600">{local}</p>}
      <ErrorNote error={error} fallback="That did not go through." />
      <div className="flex gap-2">
        <Button type="submit" variant="primary" disabled={busy}>{busy ? 'Saving…' : submitLabel}</Button>
        <Button onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  )
}
