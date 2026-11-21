import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { apiErrorMessage } from '@/lib/auth'
import { useCreateTrip } from '@/features/trips/api'
import { STYLE_TAGS, type StyleTag } from '@/features/trips/types'
import { DestinationPicker } from '@/features/trips/DestinationPicker'

const MAX_DAYS = 30
const BUDGET_MIN = 1000
const BUDGET_SLIDER_MAX = 500000
const BUDGET_MAX = 10000000

function today(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function addDays(iso: string, n: number): string {
  const [y, m, d] = iso.split('-').map(Number)
  const date = new Date(y, m - 1, d + n)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

/** Pre-filled from the budget recommender's "Plan this trip" link, if any. */
function fromLink(params: URLSearchParams) {
  const start = /^\d{4}-\d{2}-\d{2}$/.test(params.get('start') ?? '') ? params.get('start')! : today()
  const days = Math.min(Math.max(Number(params.get('days')) || 1, 1), MAX_DAYS)
  const tags = (params.get('tags') ?? '')
    .split(',')
    .filter((t): t is StyleTag => (STYLE_TAGS as readonly string[]).includes(t))
  return {
    destination: params.get('destination') ?? '',
    start,
    end: addDays(start, days - 1),
    budget: Number(params.get('budget')) || 25000,
    travelers: Math.min(Math.max(Number(params.get('travelers')) || 2, 1), 20),
    tags: [...new Set(tags)],
  }
}

export function NewTripPage() {
  const navigate = useNavigate()
  const createTrip = useCreateTrip()
  const [params] = useSearchParams()
  const [initial] = useState(() => fromLink(params))

  const [destination, setDestination] = useState(initial.destination)
  const [startDate, setStartDate] = useState(initial.start)
  const [endDate, setEndDate] = useState(initial.end)
  const [budget, setBudget] = useState(initial.budget)
  const [travelers, setTravelers] = useState(initial.travelers)
  const [tags, setTags] = useState<StyleTag[]>(initial.tags)
  const [useMemory, setUseMemory] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const days =
    Math.floor(
      (new Date(endDate).getTime() - new Date(startDate).getTime()) / 86_400_000,
    ) + 1

  function toggleTag(tag: StyleTag) {
    setTags((current) =>
      current.includes(tag) ? current.filter((t) => t !== tag) : [...current, tag],
    )
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)

    if (days < 1) {
      setError('The end date cannot be before the start date.')
      return
    }
    if (!budget || budget < BUDGET_MIN || budget > BUDGET_MAX) {
      setError(`Enter a budget between ₹${BUDGET_MIN.toLocaleString('en-IN')} and ₹${BUDGET_MAX.toLocaleString('en-IN')}.`)
      return
    }
    if (days > MAX_DAYS) {
      setError(`Trips longer than ${MAX_DAYS} days are not supported yet.`)
      return
    }

    try {
      const trip = await createTrip.mutateAsync({
        destination: destination.trim(),
        start_date: startDate,
        end_date: endDate,
        budget,
        travelers,
        style_tags: tags,
        use_memory: useMemory,
      })
      navigate(`/trips/${trip.id}`)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not create the trip.'))
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">✈️ Plan a new trip</h1>
        <p className="mt-1 text-sm text-slate-600">
          {days >= 1 ? `${days} day${days > 1 ? 's' : ''}` : 'Pick your dates'}
        </p>
        <p className="mt-2 text-sm">
          <Link to="/trips/new/own" className="font-medium text-indigo-700 hover:underline">
            Already know your plan? Write it yourself instead
          </Link>
        </p>
      </div>

      <div className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <DestinationPicker value={destination} onChange={setDestination} />

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-700">Start date</span>
            <input
              required
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500"
            />
          </label>

          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-700">End date</span>
            <input
              required
              type="date"
              min={startDate}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500"
            />
          </label>
        </div>

        <div className="block text-sm">
          <label htmlFor="budget-input" className="mb-1 flex items-center justify-between font-medium text-slate-700">
            <span>Total budget</span>
            <span className="font-normal text-slate-500">
              ₹{(budget || 0).toLocaleString('en-IN')}
            </span>
          </label>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={BUDGET_MIN}
              max={BUDGET_SLIDER_MAX}
              step={1000}
              value={Math.min(Math.max(budget || BUDGET_MIN, BUDGET_MIN), BUDGET_SLIDER_MAX)}
              onChange={(e) => setBudget(Number(e.target.value))}
              aria-label="Budget slider"
              className="w-full"
            />
            <div className="relative w-40 shrink-0">
              <span className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-500">₹</span>
              <input
                id="budget-input"
                type="number"
                inputMode="numeric"
                required
                min={BUDGET_MIN}
                max={BUDGET_MAX}
                step={1}
                value={budget || ''}
                onChange={(e) => setBudget(e.target.value === '' ? 0 : Number(e.target.value))}
                placeholder="25000"
                className="w-full rounded border border-slate-300 py-2 pr-2 pl-7 outline-none focus:border-indigo-500"
              />
            </div>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Drag the slider or type an exact amount (₹{BUDGET_MIN.toLocaleString('en-IN')} – ₹{BUDGET_MAX.toLocaleString('en-IN')}).
          </p>
        </div>

        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Travellers</span>
          <input
            type="number"
            min={1}
            max={20}
            value={travelers}
            onChange={(e) => setTravelers(Number(e.target.value))}
            className="w-24 rounded border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500"
          />
        </label>

        <fieldset>
          <legend className="mb-2 text-sm font-medium text-slate-700">
            What are you after?
          </legend>
          <div className="flex flex-wrap gap-2">
            {STYLE_TAGS.map((tag) => {
              const on = tags.includes(tag)
              return (
                <button
                  key={tag}
                  type="button"
                  aria-pressed={on}
                  onClick={() => toggleTag(tag)}
                  className={`rounded-full border px-4 py-1.5 text-sm capitalize ${
                    on
                      ? 'border-indigo-600 bg-indigo-600 text-white'
                      : 'border-slate-300 text-slate-700 hover:border-slate-500'
                  }`}
                >
                  {tag}
                </button>
              )
            })}
          </div>
        </fieldset>

        <label className="flex items-start gap-3 rounded border border-slate-200 bg-slate-50 p-3 text-sm">
          <input
            type="checkbox"
            checked={useMemory}
            onChange={(e) => setUseMemory(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            <span className="font-medium">Use my past trip preferences</span>
            <span className="mt-0.5 block text-slate-600">
              Finds your most similar past trips and plans around what you
              chose then.
            </span>
          </span>
        </label>
      </div>

      {error && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={createTrip.isPending}
        className="w-full rounded-lg bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-indigo-700 disabled:opacity-50"
      >
        {createTrip.isPending ? 'Saving…' : 'Create trip'}
      </button>
    </form>
  )
}
