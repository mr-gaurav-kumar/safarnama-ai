import { useMemo, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiErrorMessage } from '@/lib/auth'
import { Icon } from '@/components/Icon'
import { SuggestInput } from '@/components/SuggestInput'
import { PACKING_ITEMS } from './vocabulary'
import { formatDate } from '@/features/trips/api'
import {
  CATEGORIES, useAddItem, useAddMany, useDeleteItem, usePackingList, useResetTicks, useSuggestions, useUpdateItem,
  type Category, type PackingItem, type Suggestion,
} from './api'

type Mode = 'going' | 'return'

/**
 * A trip's packing list. Pack once to leave ("Going") and again to come home
 * ("Coming back") -- the second pass is what stops a charger being left in
 * the hotel. Suggestions follow the weather the trip falls in: jackets,
 * thermals and boots for a cold hill trip; half-sleeves, shorts and
 * sunscreen for a hot or beach one.
 */
export function PackingPage() {
  const { id = '' } = useParams()
  const list = usePackingList(id)
  const [mode, setMode] = useState<Mode>('going')
  const [suggesting, setSuggesting] = useState(false)
  const reset = useResetTicks(id)

  if (list.isPending) return <p className="text-sm text-slate-500">Loading your packing list…</p>
  if (list.isError || !list.data) {
    return (
      <p className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
        {apiErrorMessage(list.error, 'Could not load the packing list.')}
      </p>
    )
  }

  const data = list.data
  const { total } = data.progress
  const done = mode === 'going' ? data.progress.packed_going : data.progress.packed_return
  const left = total - done
  const pct = total ? Math.round((done / total) * 100) : 0

  return (
    <div className="space-y-8">
      <header className="space-y-4">
        <Link to={`/trips/${id}`} className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900">
          <Icon name="back" className="h-4 w-4" /> Back to the trip
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-indigo-700">Packing list</p>
            <h1 className="font-display mt-1 text-4xl tracking-tight sm:text-5xl">{data.destination.split(',')[0]}</h1>
            <p className="mt-1 text-slate-600">
              {formatDate(data.start_date)} – {formatDate(data.end_date)}
            </p>
          </div>
          <button
            onClick={() => setSuggesting((v) => !v)}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-3 text-sm font-semibold text-white shadow-md hover:opacity-95"
          >
            <Icon name="spark" className="h-4 w-4" /> {suggesting ? 'Hide suggestions' : 'Suggest what to pack'}
          </button>
        </div>
      </header>

      {suggesting && <SuggestionPanel tripId={id} onDone={() => setSuggesting(false)} />}

      {/* ---- going / coming back + progress ---- */}
      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="inline-flex rounded-xl bg-slate-100 p-1 text-sm">
            {(['going', 'return'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`rounded-lg px-4 py-2 ${mode === m ? 'bg-white font-semibold shadow-sm' : 'text-slate-600'}`}
              >
                {m === 'going' ? '🧳 Packing to leave' : '🏠 Packing to come home'}
              </button>
            ))}
          </div>
          {done > 0 && (
            <button
              onClick={() => reset.mutate(mode)}
              disabled={reset.isPending}
              className="text-sm text-slate-500 hover:text-slate-900 disabled:opacity-50"
            >
              Untick all
            </button>
          )}
        </div>

        <div>
          <div className="mb-2 flex justify-between text-sm">
            <span className="font-medium text-slate-800">
              {done} of {total} packed
            </span>
            <span className="text-slate-500">{pct}%</span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full transition-all ${pct === 100 ? 'bg-emerald-500' : 'bg-indigo-600'}`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {total > 0 && (
          <p
            className={`rounded-xl px-4 py-3 text-sm ${
              left === 0 ? 'bg-emerald-50 text-emerald-800' : mode === 'return' ? 'bg-amber-50 text-amber-900' : 'bg-slate-50 text-slate-700'
            }`}
          >
            {left === 0
              ? mode === 'going'
                ? '✅ Everything is packed. Have a great trip!'
                : '✅ Everything is packed for home. Nothing left behind.'
              : mode === 'going'
                ? `Tick each item as it goes into the bag — ${left} still to pack.`
                : `Before you check out: ${left} item${left > 1 ? 's' : ''} not packed yet. Check the room, bathroom and charger points.`}
          </p>
        )}
      </section>

      <AddItemForm tripId={id} />

      {total === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
          <p className="font-medium text-slate-800">Your list is empty</p>
          <p className="mt-1 text-sm text-slate-500">
            Get suggestions based on the weather and your trip, or add items yourself.
          </p>
          <button onClick={() => setSuggesting(true)} className="mt-4 text-sm font-semibold text-indigo-700 hover:underline">
            Suggest what to pack →
          </button>
        </div>
      ) : (
        <ItemGroups tripId={id} items={data.items} mode={mode} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------- the list

function ItemGroups({ tripId, items, mode }: { tripId: string; items: PackingItem[]; mode: Mode }) {
  const groups = useMemo(
    () => CATEGORIES.map((c) => ({ ...c, items: items.filter((i) => i.category === c.key) })).filter((g) => g.items.length),
    [items],
  )
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {groups.map((g) => {
        const packed = g.items.filter((i) => (mode === 'going' ? i.packed_going : i.packed_return)).length
        return (
          <section key={g.key} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-3 flex items-center justify-between font-semibold">
              <span>
                {g.emoji} {g.label}
              </span>
              <span className="text-xs font-normal text-slate-500">
                {packed}/{g.items.length}
              </span>
            </h2>
            <ul className="divide-y divide-slate-100">
              {g.items.map((i) => <ItemRow key={i.id} tripId={tripId} item={i} mode={mode} />)}
            </ul>
          </section>
        )
      })}
    </div>
  )
}

function ItemRow({ tripId, item, mode }: { tripId: string; item: PackingItem; mode: Mode }) {
  const update = useUpdateItem(tripId)
  const del = useDeleteItem(tripId)
  const checked = mode === 'going' ? item.packed_going : item.packed_return
  const busy = update.isPending || del.isPending

  return (
    <li className="flex items-center gap-3 py-2.5">
      <input
        type="checkbox"
        checked={checked}
        disabled={busy}
        onChange={(e) => update.mutate({ id: item.id, [mode === 'going' ? 'packed_going' : 'packed_return']: e.target.checked })}
        className="h-5 w-5 shrink-0 accent-indigo-600"
        aria-label={`Packed ${item.name}`}
      />
      <div className="min-w-0 flex-1">
        <p className={`truncate text-[15px] ${checked ? 'text-slate-400 line-through' : 'text-slate-900'}`}>{item.name}</p>
        <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px]">
          {item.locked && <span className="rounded bg-amber-100 px-1.5 py-0.5 font-medium text-amber-800">🔒 Added by admin</span>}
          {item.source === 'ai' && <span className="rounded bg-indigo-50 px-1.5 py-0.5 font-medium text-indigo-700">✨ Suggested</span>}
          {item.note && <span className="text-slate-500">{item.note}</span>}
          {mode === 'return' && !item.packed_going && <span className="text-slate-400">not packed when leaving</span>}
        </div>
      </div>

      {item.locked ? (
        <span className="rounded-lg bg-slate-50 px-2.5 py-1 text-sm font-medium tabular-nums text-slate-700">× {item.quantity}</span>
      ) : (
        <div className="flex items-center rounded-lg border border-slate-200 text-sm">
          <button
            type="button"
            disabled={busy || item.quantity <= 1}
            onClick={() => update.mutate({ id: item.id, quantity: item.quantity - 1 })}
            className="px-2 py-1 text-slate-500 hover:text-slate-900 disabled:opacity-30"
            aria-label="Fewer"
          >
            −
          </button>
          <span className="min-w-[1.75rem] text-center font-medium tabular-nums">{item.quantity}</span>
          <button
            type="button"
            disabled={busy || item.quantity >= 99}
            onClick={() => update.mutate({ id: item.id, quantity: item.quantity + 1 })}
            className="px-2 py-1 text-slate-500 hover:text-slate-900 disabled:opacity-30"
            aria-label="More"
          >
            +
          </button>
        </div>
      )}

      {!item.locked && (
        <button
          type="button"
          disabled={busy}
          onClick={() => del.mutate(item.id)}
          className="rounded-md p-1 text-slate-300 hover:bg-red-50 hover:text-red-600"
          aria-label={`Remove ${item.name}`}
        >
          <Icon name="close" className="h-4 w-4" />
        </button>
      )}
    </li>
  )
}

// ---------------------------------------------------------------- add your own

const PACK_OPTIONS = PACKING_ITEMS.map(([value, c]) => ({ value, hint: CATEGORIES.find((x) => x.key === c)?.label }))

function AddItemForm({ tripId }: { tripId: string }) {
  const add = useAddItem(tripId)
  const [name, setName] = useState('')
  const [category, setCategory] = useState<Category>('clothes')
  const [quantity, setQuantity] = useState(1)

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    add.mutate({ name: name.trim(), category, quantity }, { onSuccess: () => { setName(''); setQuantity(1) } })
  }

  const field = 'rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-[15px] outline-none focus:border-slate-900'
  return (
    <form onSubmit={submit} className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <span className="min-w-0 flex-1">
          <SuggestInput
            value={name}
            onChange={setName}
            options={PACK_OPTIONS}
            onPick={(o) => {
              const hit = PACKING_ITEMS.find(([n]) => n === o.value)
              if (hit) setCategory(hit[1])
            }}
            maxLength={80}
            placeholder="Add an item, e.g. Vest"
            className={field}
          />
        </span>
        <select value={category} onChange={(e) => setCategory(e.target.value as Category)} className={field}>
          {CATEGORIES.map((c) => <option key={c.key} value={c.key}>{c.emoji} {c.label}</option>)}
        </select>
        <input
          type="number"
          min={1}
          max={99}
          value={quantity}
          onChange={(e) => setQuantity(Math.min(99, Math.max(1, Number(e.target.value) || 1)))}
          className={`${field} w-20`}
          aria-label="Quantity"
        />
        <button type="submit" disabled={add.isPending || !name.trim()} className="rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-40">
          Add
        </button>
      </div>
      {add.isError && <p className="text-sm text-red-600">{apiErrorMessage(add.error, 'Could not add that item.')}</p>}
    </form>
  )
}

// ---------------------------------------------------------------- suggestions

function SuggestionPanel({ tripId, onDone }: { tripId: string; onDone: () => void }) {
  const s = useSuggestions(tripId, true)
  const addMany = useAddMany(tripId)
  // Unticked = skip; a changed number = the quantity to add.
  const [skip, setSkip] = useState<Set<string>>(new Set())
  const [qty, setQty] = useState<Record<string, number>>({})

  const items = s.data?.items ?? []
  const chosen = items.filter((i) => !skip.has(i.name))
  const grouped = CATEGORIES.map((c) => ({ ...c, items: items.filter((i) => i.category === c.key) })).filter((g) => g.items.length)

  function toggle(name: string) {
    setSkip((cur) => {
      const next = new Set(cur)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  function addChosen() {
    addMany.mutate(
      chosen.map((i: Suggestion) => ({ name: i.name, category: i.category, quantity: qty[i.name] ?? i.quantity })),
      { onSuccess: onDone },
    )
  }

  return (
    <section className="space-y-5 rounded-2xl border border-indigo-200 bg-indigo-50/40 p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <Icon name="spark" className="h-5 w-5 text-indigo-600" /> Suggested for this trip
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {s.data?.source === 'ai' ? 'Written by AI from your trip and its weather.' : 'Based on the weather, the place and your trip style.'}{' '}
            Untick anything you don’t need and change the numbers.
          </p>
        </div>
        {s.data && s.data.context.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {s.data.context.map((c) => (
              <span key={c} className="rounded-full bg-white px-3 py-1 text-xs text-slate-700 ring-1 ring-slate-200">{c}</span>
            ))}
          </div>
        )}
      </div>

      {s.isPending && <p className="text-sm text-slate-500">Checking the weather and thinking about what you need…</p>}
      {s.isError && <p className="text-sm text-red-600">{apiErrorMessage(s.error, 'Could not get suggestions.')}</p>}
      {s.data && items.length === 0 && <p className="text-sm text-slate-600">Everything we would suggest is already on your list. 👍</p>}

      {items.length > 0 && (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            {grouped.map((g) => (
              <div key={g.key} className="rounded-xl bg-white p-4 ring-1 ring-slate-200">
                <h3 className="mb-2 text-sm font-semibold">{g.emoji} {g.label}</h3>
                <ul className="space-y-2">
                  {g.items.map((i) => (
                    <li key={i.name} className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={!skip.has(i.name)}
                        onChange={() => toggle(i.name)}
                        className="mt-1 h-4 w-4 shrink-0 accent-indigo-600"
                        aria-label={i.name}
                      />
                      <div className="min-w-0 flex-1">
                        <p className={`text-sm ${skip.has(i.name) ? 'text-slate-400 line-through' : 'text-slate-900'}`}>{i.name}</p>
                        {i.reason && <p className="text-xs text-slate-500">{i.reason}</p>}
                      </div>
                      <input
                        type="number"
                        min={1}
                        max={99}
                        value={qty[i.name] ?? i.quantity}
                        onChange={(e) => setQty((q) => ({ ...q, [i.name]: Math.min(99, Math.max(1, Number(e.target.value) || 1)) }))}
                        className="w-14 rounded-lg border border-slate-200 px-2 py-1 text-sm"
                        aria-label={`How many ${i.name}`}
                      />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={addChosen}
              disabled={addMany.isPending || chosen.length === 0}
              className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-40"
            >
              {addMany.isPending ? 'Adding…' : `Add ${chosen.length} item${chosen.length === 1 ? '' : 's'} to my list`}
            </button>
            <button onClick={onDone} className="text-sm text-slate-500 hover:text-slate-900">Cancel</button>
          </div>
          {addMany.isError && <p className="text-sm text-red-600">{apiErrorMessage(addMany.error, 'Could not add the items.')}</p>}
        </>
      )}
    </section>
  )
}
