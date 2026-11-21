import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiErrorMessage } from '@/lib/auth'
import { useCopyTrip } from '@/features/trips/api'
import type { TripDetail } from '@/features/trips/types'

function nextWeek(): string {
  const d = new Date()
  d.setDate(d.getDate() + 7)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Edit the days (owner), or plan the same trip again on new dates (anyone on it). */
export function PlanActions({ trip }: { trip: TripDetail }) {
  const navigate = useNavigate()
  const copyTrip = useCopyTrip()
  const [open, setOpen] = useState(false)
  const [start, setStart] = useState(nextWeek())
  const [error, setError] = useState<string | null>(null)

  async function planAgain() {
    setError(null)
    try {
      const copy = await copyTrip.mutateAsync({ id: trip.id, start_date: start })
      setOpen(false)
      navigate(`/trips/${copy.id}`)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not copy the plan.'))
    }
  }

  const button =
    'rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50'

  return (
    <div className="flex flex-wrap items-center gap-3">
      {trip.role === 'owner' && (
        <Link to={`/trips/${trip.id}/edit`} className={button}>
          Edit plan
        </Link>
      )}
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className={button}>
        Plan this again
      </button>
      {open && (
        <div className="flex w-full flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          <label className="text-sm">
            <span className="mb-1 block font-medium text-slate-700">New start date</span>
            <input type="date" value={start} onChange={(e) => setStart(e.target.value)}
              className="rounded border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500" />
          </label>
          <button type="button" onClick={planAgain} disabled={!start || copyTrip.isPending}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
            {copyTrip.isPending ? 'Copying…' : 'Create the new trip'}
          </button>
          <p className="basis-full text-xs text-slate-500">
            Same days and notes on the new dates, with your packing list. Tickets are not copied.
          </p>
          {error && <p role="alert" className="basis-full text-sm text-red-700">{error}</p>}
        </div>
      )}
    </div>
  )
}
