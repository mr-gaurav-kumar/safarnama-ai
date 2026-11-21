import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { CATEGORIES, type Category, type PackingList } from '@/features/packing/api'
import { ACTIVITIES, PACKING_ITEMS } from '@/features/packing/vocabulary'
import { SuggestInput, type SuggestOption } from '@/components/SuggestInput'
import { apiErrorMessage } from '@/lib/auth'
import { formatDate, formatINR, useCreateOwnPlan, useEditPlan, useFillPlan, useTrip, type PlanDayInput } from '@/features/trips/api'
import { DestinationPicker } from '@/features/trips/DestinationPicker'
import { STYLE_TAGS, type StyleTag, type TripDetail } from '@/features/trips/types'

const MAX_DAYS = 30
const MAX_ITEMS = 25

interface Row {
  key: number
  time: string
  activity: string
  place: string
  cost: string
}

interface PackRow {
  key: number
  name: string
  category: Category
  qty: number
}

let nextKey = 1
const blankRow = (): Row => ({ key: nextKey++, time: '', activity: '', place: '', cost: '' })
const packRow = (name = '', category: Category = 'other', qty = 1): PackRow => ({ key: nextKey++, name, category, qty })

/** One tap adds the things almost everyone takes. */
const QUICK: [string, Category][] = [
  ['Aadhaar card', 'documents'], ['Tickets', 'documents'], ['Phone charger', 'electronics'], ['Power bank', 'electronics'],
  ['Toothbrush & paste', 'toiletries'], ['Medicines', 'health'], ['Water bottle', 'accessories'], ['Sunglasses', 'accessories'],
  ['T-shirts', 'clothes'], ['Jacket', 'clothes'], ['Comfortable shoes', 'footwear'], ['Cash', 'documents'],
]

function today(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function addDays(iso: string, n: number): string {
  const [y, m, d] = iso.split('-').map(Number)
  const date = new Date(y, m - 1, d + n)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function dayCount(start: string, end: string): number {
  return Math.floor((new Date(end).getTime() - new Date(start).getTime()) / 86_400_000) + 1
}

function rowsFromTrip(trip: TripDetail): Row[][] {
  return (trip.itinerary?.day_plan ?? []).map((d) =>
    d.items.map((i) => ({
      key: nextKey++,
      time: i.time ?? '',
      activity: i.activity ?? '',
      place: i.place ?? '',
      cost: i.estimated_cost ? String(i.estimated_cost) : '',
    })),
  )
}

/** Write a plan yourself (/trips/new/own), or change the days of one you own (/trips/:id/edit). */
export function PlanEditorPage() {
  const { id } = useParams<{ id: string }>()
  const editing = Boolean(id)
  const navigate = useNavigate()
  const existing = useTrip(id)
  const createPlan = useCreateOwnPlan()
  const editPlan = useEditPlan(id ?? '')

  const [destination, setDestination] = useState('')
  const [startDate, setStartDate] = useState(today())
  const [endDate, setEndDate] = useState(addDays(today(), 2))
  const [travelers, setTravelers] = useState(2)
  const [budget, setBudget] = useState('')
  const [tags, setTags] = useState<StyleTag[]>([])
  const [notes, setNotes] = useState('')
  const [days, setDays] = useState<Row[][]>([[blankRow()], [blankRow()], [blankRow()]])
  const [packing, setPacking] = useState<PackRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const fillPlan = useFillPlan()
  const [fillNote, setFillNote] = useState<string | null>(null)
  const [undo, setUndo] = useState<{ days: Row[][]; packing: PackRow[] } | null>(null)
  const loaded = useRef(false)
  const packLoaded = useRef(false)

  // Editing: the traveller's own packing items (admin items stay on the Packing page).
  const savedPacking = useQuery({
    queryKey: ['packing', id ?? ''],
    queryFn: async () => (await api.get<PackingList>(`/trips/${id}/packing`)).data,
    enabled: editing,
  })
  const lockedCount = savedPacking.data?.items.filter((i) => i.locked).length ?? 0

  // Sights at the destination, for the "Where" and "What" suggestions.
  const place = (editing ? existing.data?.destination : destination)?.trim() ?? ''
  const sights = useQuery({
    queryKey: ['attractions', place.toLowerCase()],
    queryFn: async () => (await api.get<string[]>('/geo/attractions', { params: { destination: place } })).data,
    enabled: place.length >= 2,
    staleTime: Infinity,
  })
  const placeOptions = useMemo<SuggestOption[]>(() => (sights.data ?? []).map((v) => ({ value: v })), [sights.data])
  const activityOptions = useMemo<SuggestOption[]>(
    () => [
      ...(sights.data ?? []).map((v) => ({ value: `Visit ${v}`, hint: 'sight' })),
      ...ACTIVITIES.map((v) => ({ value: v })),
    ],
    [sights.data],
  )
  const packOptions = useMemo<SuggestOption[]>(
    () => PACKING_ITEMS.map(([v, c]) => ({ value: v, hint: CATEGORIES.find((x) => x.key === c)?.label })),
    [],
  )
  useEffect(() => {
    if (!editing || !savedPacking.data || packLoaded.current) return
    packLoaded.current = true
    setPacking(savedPacking.data.items.filter((i) => !i.locked).map((i) => packRow(i.name, i.category as Category, i.quantity)))
  }, [editing, savedPacking.data])

  // Editing: start from the saved plan, once.
  useEffect(() => {
    const trip = existing.data
    if (!editing || !trip || loaded.current) return
    loaded.current = true
    setDestination(trip.destination)
    setStartDate(trip.start_date)
    setEndDate(trip.end_date)
    setNotes(trip.itinerary?.explanation ?? '')
    const rows = rowsFromTrip(trip)
    setDays(rows.length ? rows.map((r) => (r.length ? r : [blankRow()])) : [[blankRow()]])
  }, [editing, existing.data])

  const total = dayCount(startDate, endDate)

  // New plan: one card per day of the trip, keeping what was already typed.
  useEffect(() => {
    if (editing || !(total >= 1 && total <= MAX_DAYS)) return
    setDays((current) =>
      current.length === total
        ? current
        : Array.from({ length: total }, (_, i) => current[i] ?? [blankRow()]),
    )
  }, [editing, total])

  function updateRow(day: number, key: number, change: Partial<Row>) {
    setDays((all) => all.map((rows, d) => (d === day ? rows.map((r) => (r.key === key ? { ...r, ...change } : r)) : rows)))
  }
  function addRow(day: number) {
    setDays((all) => all.map((rows, d) => (d === day && rows.length < MAX_ITEMS ? [...rows, blankRow()] : rows)))
  }
  function removeRow(day: number, key: number) {
    setDays((all) => all.map((rows, d) => (d === day ? rows.filter((r) => r.key !== key) : rows)))
  }
  function addPack(name = '', category: Category = 'other') {
    setPacking((p) => {
      if (name && p.some((r) => r.name.trim().toLowerCase() === name.toLowerCase())) return p
      return p.length >= 150 ? p : [...p, packRow(name, category)]
    })
  }
  function updatePack(key: number, change: Partial<PackRow>) {
    setPacking((p) => p.map((r) => (r.key === key ? { ...r, ...change } : r)))
  }
  function removePack(key: number) {
    setPacking((p) => p.filter((r) => r.key !== key))
  }

  function toggleTag(tag: StyleTag) {
    setTags((t) => (t.includes(tag) ? t.filter((x) => x !== tag) : [...t, tag]))
  }

  const planned = days.flat().reduce((sum, r) => sum + (Number(r.cost) || 0), 0)

  async function fillRest() {
    setError(null)
    setFillNote(null)
    const trip = existing.data
    const dest = (editing ? trip?.destination : destination)?.trim() ?? ''
    if (dest.length < 2) return setError('Add the destination first, then AI can fill the rest.')
    if (!editing && (total < 1 || total > MAX_DAYS)) return setError('Pick valid dates first.')
    try {
      const result = await fillPlan.mutateAsync({
        destination: dest,
        start_date: editing && trip ? trip.start_date : startDate,
        end_date: editing && trip ? trip.end_date : endDate,
        travelers: editing && trip ? trip.travelers : travelers,
        budget: editing && trip ? Number(trip.budget) : Math.max(0, Number(budget) || 0),
        style_tags: editing && trip ? trip.style_tags : tags,
        notes: notes.trim() || null,
        days: days.map((rows) => ({
          items: rows
            .filter((r) => r.activity.trim())
            .map((r) => ({ time: r.time, activity: r.activity.trim(), place: r.place.trim(), estimated_cost: Math.max(0, Number(r.cost) || 0) })),
        })),
        packing: packing.filter((r) => r.name.trim()).map((r) => ({ name: r.name.trim(), category: r.category, quantity: r.qty || 1 })),
      })
      setUndo({ days, packing })
      setDays(
        result.days.map((d) =>
          d.items.length
            ? d.items.map((i) => ({ key: nextKey++, time: i.time, activity: i.activity, place: i.place, cost: i.estimated_cost ? String(i.estimated_cost) : '' }))
            : [blankRow()],
        ),
      )
      setPacking((p) => [...p.filter((r) => r.name.trim()), ...result.packing.map((i) => packRow(i.name, i.category as Category, i.quantity))])
      const what = [
        result.added_items && `${result.added_items} activit${result.added_items === 1 ? 'y' : 'ies'}`,
        result.filled_fields && `${result.filled_fields} blank${result.filled_fields === 1 ? '' : 's'} filled`,
        result.packing.length && `${result.packing.length} packing item${result.packing.length === 1 ? '' : 's'}`,
      ].filter(Boolean).join(', ')
      setFillNote(
        (what ? `Added ${what}` : 'Nothing to add — your plan already looks complete') +
          (result.source === 'ai' ? ' (by Gemini).' : ' (from our travel lists — AI is not connected).') +
          ' Check it, change anything, then save.',
      )
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not fill the plan.'))
    }
  }

  function undoFill() {
    if (!undo) return
    setDays(undo.days)
    setPacking(undo.packing)
    setUndo(null)
    setFillNote(null)
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (!editing) {
      if (destination.trim().length < 2) return setError('Where are you going? Add a destination.')
      if (total < 1) return setError('The end date cannot be before the start date.')
      if (total > MAX_DAYS) return setError(`Trips longer than ${MAX_DAYS} days are not supported yet.`)
    }
    const payloadDays: PlanDayInput[] = days.map((rows) => ({
      items: rows
        .filter((r) => r.activity.trim())
        .map((r) => ({
          time: r.time,
          activity: r.activity.trim(),
          place: r.place.trim(),
          estimated_cost: Math.max(0, Number(r.cost) || 0),
        })),
    }))
    if (!payloadDays.some((d) => d.items.length)) return setError('Add at least one activity to save the plan.')
    const payloadPacking = packing
      .filter((r) => r.name.trim())
      .map((r) => ({ name: r.name.trim().slice(0, 80), category: r.category, quantity: Math.min(Math.max(r.qty || 1, 1), 99) }))

    try {
      if (editing && id) {
        await editPlan.mutateAsync({ days: payloadDays, notes, packing: payloadPacking })
        navigate(`/trips/${id}`)
      } else {
        const trip = await createPlan.mutateAsync({
          destination: destination.trim(),
          start_date: startDate,
          end_date: endDate,
          travelers,
          budget: Math.max(0, Number(budget) || 0),
          style_tags: tags,
          notes: notes.trim() || null,
          days: payloadDays,
          packing: payloadPacking,
        })
        navigate(`/trips/${trip.id}`)
      }
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not save the plan.'))
    }
  }

  if (editing && existing.isPending) return <p className="text-sm text-slate-500">Loading your plan…</p>
  if (editing && (existing.isError || !existing.data)) {
    return (
      <p className="text-sm text-slate-600">
        That trip could not be found. <Link to="/dashboard" className="underline">Back to dashboard</Link>
      </p>
    )
  }
  if (editing && existing.data && existing.data.role !== 'owner') {
    return <p className="text-sm text-slate-600">Only the trip owner can edit this plan.</p>
  }

  const saving = createPlan.isPending || editPlan.isPending

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{editing ? `Edit your ${existing.data?.destination} plan` : 'Write your own plan'}</h1>
        <p className="mt-1 text-sm text-slate-600">
          {editing
            ? `${formatDate(startDate)} – ${formatDate(endDate)}. Change, add or remove anything, then save.`
            : 'No AI here: add what you have planned, day by day. You can download it as a PDF, keep it for later or plan it again on new dates.'}
        </p>
        {!editing && (
          <p className="mt-2 text-sm">
            <Link to="/trips/new" className="font-medium text-indigo-700 hover:underline">
              Prefer a ready plan? Let AI plan it instead
            </Link>
          </p>
        )}
      </div>

      {!editing && (
        <div className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <DestinationPicker value={destination} onChange={setDestination} />
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700">Start date</span>
              <input required type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500" />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700">End date</span>
              <input required type="date" min={startDate} value={endDate} onChange={(e) => setEndDate(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500" />
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700">Travellers</span>
              <input type="number" min={1} max={20} value={travelers} onChange={(e) => setTravelers(Number(e.target.value))}
                className="w-24 rounded border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500" />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700">Total budget <span className="font-normal text-slate-500">(optional)</span></span>
              <span className="relative block w-48">
                <span className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-500">₹</span>
                <input type="number" inputMode="numeric" min={0} max={10000000} value={budget}
                  onChange={(e) => setBudget(e.target.value)} placeholder="25000"
                  className="w-full rounded border border-slate-300 py-2 pr-2 pl-7 outline-none focus:border-indigo-500" />
              </span>
            </label>
          </div>
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-slate-700">What kind of trip is it?</legend>
            <div className="flex flex-wrap gap-2">
              {STYLE_TAGS.map((tag) => {
                const on = tags.includes(tag)
                return (
                  <button key={tag} type="button" aria-pressed={on} onClick={() => toggleTag(tag)}
                    className={`rounded-full border px-4 py-1.5 text-sm capitalize ${on ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-slate-300 text-slate-700 hover:border-slate-500'}`}>
                    {tag}
                  </button>
                )
              })}
            </div>
          </fieldset>
        </div>
      )}

      <label className="block text-sm">
        <span className="mb-1 block font-medium text-slate-700">Notes <span className="font-normal text-slate-500">(optional)</span></span>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={2000} rows={2}
          placeholder="Who is coming, what to remember, anything else"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500" />
      </label>

      <section className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-lg font-medium">Day by day</h2>
          {planned > 0 && <span className="text-sm text-slate-500">Planned spend {formatINR(planned)}</span>}
        </div>
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-indigo-100 bg-indigo-50/60 px-4 py-3">
          <button type="button" onClick={fillRest} disabled={fillPlan.isPending}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
            {fillPlan.isPending ? 'Filling…' : '✨ Fill the rest with AI'}
          </button>
          <span className="flex-1 text-sm text-slate-600">
            {fillNote ?? 'Write what you know; AI adds activities for empty days, fills blank times, places and costs, and suggests what to pack. Your entries stay as they are.'}
          </span>
          {undo && (
            <button type="button" onClick={undoFill} className="text-sm font-medium text-indigo-700 hover:underline">
              Undo
            </button>
          )}
        </div>
        {total > MAX_DAYS && !editing && (
          <p className="text-sm text-red-700">Pick dates up to {MAX_DAYS} days apart.</p>
        )}
        {days.map((rows, d) => (
          <article key={d} className="rounded-xl border border-slate-200 bg-white">
            <header className="flex items-baseline justify-between border-b border-slate-100 px-4 py-3">
              <h3 className="font-medium">Day {d + 1}</h3>
              <span className="text-sm text-slate-500">{formatDate(addDays(startDate, d))}</span>
            </header>
            <ul className="space-y-3 p-4">
              {rows.map((r) => (
                <li key={r.key} className="grid grid-cols-[6.5rem_1fr_auto] gap-2 sm:grid-cols-[6.5rem_1.4fr_1fr_7rem_auto]">
                  <input type="time" value={r.time} aria-label="Time" onChange={(e) => updateRow(d, r.key, { time: e.target.value })}
                    className="rounded border border-slate-300 px-2 py-2 text-sm outline-none focus:border-indigo-500" />
                  <SuggestInput value={r.activity} maxLength={200} aria-label="Activity" placeholder="What are you doing?"
                    options={activityOptions}
                    onChange={(v) => updateRow(d, r.key, { activity: v })}
                    onPick={(o) => {
                      // "Visit Hadimba Temple" fills in where, too.
                      if (o.value.startsWith('Visit ') && !r.place) updateRow(d, r.key, { place: o.value.slice(6) })
                    }}
                    className="rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500" />
                  <button type="button" onClick={() => removeRow(d, r.key)} aria-label="Remove activity"
                    className="row-span-2 self-start rounded px-2 py-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 sm:order-last sm:row-span-1">
                    ✕
                  </button>
                  <span className="col-span-2 sm:col-span-1">
                    <SuggestInput value={r.place} maxLength={200} aria-label="Place" placeholder="Where (optional)"
                      options={placeOptions}
                      onChange={(v) => updateRow(d, r.key, { place: v })}
                      className="rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500" />
                  </span>
                  <span className="relative col-span-2 block sm:col-span-1">
                    <span className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-sm text-slate-500">₹</span>
                    <input type="number" min={0} inputMode="numeric" value={r.cost} aria-label="Cost" placeholder="Cost"
                      onChange={(e) => updateRow(d, r.key, { cost: e.target.value })}
                      className="w-full rounded border border-slate-300 py-2 pr-2 pl-6 text-sm outline-none focus:border-indigo-500" />
                  </span>
                </li>
              ))}
              {rows.length === 0 && <li className="text-sm text-slate-500">Nothing planned for this day.</li>}
            </ul>
            <div className="border-t border-slate-100 px-4 py-2.5">
              <button type="button" onClick={() => addRow(d)} disabled={rows.length >= MAX_ITEMS}
                className="text-sm font-medium text-indigo-700 hover:underline disabled:opacity-40">
                + Add activity
              </button>
            </div>
          </article>
        ))}
      </section>

      <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
        <div>
          <h2 className="text-lg font-medium">{endDate < today() ? 'What you carried' : 'What to take'}</h2>
          <p className="text-sm text-slate-500">
            {endDate < today()
              ? 'Note what you took on this trip. Plan it again later and the list comes with it.'
              : 'Your packing list. On the trip page you can tick items off while packing and get weather-based suggestions.'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {QUICK.filter(([n]) => !packing.some((r) => r.name.trim().toLowerCase() === n.toLowerCase())).map(([n, c]) => (
            <button key={n} type="button" onClick={() => addPack(n, c)}
              className="rounded-full border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:border-indigo-500 hover:text-indigo-700">
              + {n}
            </button>
          ))}
        </div>
        <ul className="space-y-2">
          {packing.map((r) => (
            <li key={r.key} className="grid grid-cols-[1fr_auto] gap-2 sm:grid-cols-[1fr_10rem_5rem_auto]">
              <SuggestInput value={r.name} maxLength={80} aria-label="Item" placeholder="Item, e.g. Woollen socks"
                options={packOptions}
                onChange={(v) => updatePack(r.key, { name: v })}
                onPick={(o) => {
                  const hit = PACKING_ITEMS.find(([n]) => n === o.value)
                  if (hit) updatePack(r.key, { name: o.value, category: hit[1] })
                }}
                className="rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500" />
              <button type="button" onClick={() => removePack(r.key)} aria-label="Remove item"
                className="row-span-2 self-start rounded px-2 py-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 sm:order-last sm:row-span-1">
                ✕
              </button>
              <span className="flex gap-2 sm:contents">
                <select value={r.category} aria-label="Category" onChange={(e) => updatePack(r.key, { category: e.target.value as Category })}
                  className="flex-1 rounded border border-slate-300 px-2 py-2 text-sm outline-none focus:border-indigo-500">
                  {CATEGORIES.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
                </select>
                <input type="number" min={1} max={99} value={r.qty} aria-label="Quantity"
                  onChange={(e) => updatePack(r.key, { qty: Number(e.target.value) })}
                  className="w-20 rounded border border-slate-300 px-2 py-2 text-sm outline-none focus:border-indigo-500" />
              </span>
            </li>
          ))}
          {packing.length === 0 && <li className="text-sm text-slate-500">Nothing on the list yet. Tap a suggestion above or add your own.</li>}
        </ul>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <button type="button" onClick={() => addPack()} className="text-sm font-medium text-indigo-700 hover:underline">
            + Add item
          </button>
          {lockedCount > 0 && (
            <span className="text-xs text-slate-500">
              Plus {lockedCount} item{lockedCount === 1 ? '' : 's'} Safarnama adds for every trip (on the Packing page).
            </span>
          )}
        </div>
      </section>

      {error && <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="flex flex-wrap gap-3">
        <button type="submit" disabled={saving}
          className="rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-indigo-700 disabled:opacity-50">
          {saving ? 'Saving…' : editing ? 'Save changes' : 'Save plan'}
        </button>
        <Link to={editing ? `/trips/${id}` : '/dashboard'}
          className="rounded-lg border border-slate-200 bg-white px-6 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50">
          Cancel
        </Link>
      </div>
    </form>
  )
}
