import { useState, type FormEvent } from 'react'
import {
  CATEGORIES, useCreateDefault, useDefaults, useDeleteDefault, useUpdateDefault,
  type Category, type PackingDefault,
} from '@/features/packing/api'
import { formatWhen } from './api'
import { Badge, Button, ConfirmButton, ErrorNote, PageHeader } from './ui'

const field = 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-900'
const label = (c: string) => CATEGORIES.find((x) => x.key === c)

/**
 * Items the admin puts on travellers' packing lists -- for everyone, or for
 * one person. They show on every trip list of the people they target,
 * marked "Added by admin"; travellers can tick them but only the admin can
 * change or remove them. Deleting one here removes it from every list.
 */
export function PackingDefaultsPage() {
  const { data, isPending, isError } = useDefaults()
  const [adding, setAdding] = useState(false)

  return (
    <>
      <PageHeader
        title="Packing defaults"
        subtitle="Items added to travellers’ packing lists. Travellers can tick them but can’t change or remove them."
      >
        <Button variant="primary" onClick={() => setAdding((v) => !v)}>{adding ? 'Close' : 'Add item'}</Button>
      </PageHeader>

      {adding && <CreateForm onDone={() => setAdding(false)} />}

      {isPending && <p className="text-sm text-slate-500">Loading…</p>}
      {isError && <p className="text-sm text-red-700">Could not load the default items.</p>}
      {data?.length === 0 && (
        <p className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
          No default items yet. Add something every traveller should carry, like a government photo ID.
        </p>
      )}

      {data && data.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <ul className="divide-y divide-slate-100">
            {data.map((d) => <Row key={d.id} d={d} />)}
          </ul>
        </div>
      )}
    </>
  )
}

function Row({ d }: { d: PackingDefault }) {
  const del = useDeleteDefault()
  const [editing, setEditing] = useState(false)
  const c = label(d.category)

  if (editing) return <li className="p-4"><EditForm d={d} onDone={() => setEditing(false)} /></li>

  return (
    <li className="flex flex-wrap items-center gap-4 px-4 py-3">
      <span className="text-xl" aria-hidden>{c?.emoji ?? '📦'}</span>
      <div className="min-w-0 flex-1">
        <p className="font-medium text-slate-900">
          {d.name} <span className="font-normal text-slate-500">× {d.quantity}</span>
        </p>
        <p className="text-xs text-slate-500">
          {c?.label ?? d.category}
          {d.note ? ` · ${d.note}` : ''} · added {formatWhen(d.created_at)}
        </p>
      </div>
      {d.user_email ? (
        <Badge tone="info">Only {d.user_name ?? d.user_email}</Badge>
      ) : (
        <Badge tone="good">Everyone</Badge>
      )}
      <Button onClick={() => setEditing(true)}>Edit</Button>
      <ConfirmButton confirmLabel="Remove from all lists" onConfirm={() => del.mutate(d.id)} disabled={del.isPending}>
        Delete
      </ConfirmButton>
      <ErrorNote error={del.error} fallback="Could not delete it." />
    </li>
  )
}

function Fields({
  name, setName, category, setCategory, quantity, setQuantity, note, setNote,
}: {
  name: string; setName: (v: string) => void
  category: Category; setCategory: (v: Category) => void
  quantity: number; setQuantity: (v: number) => void
  note: string; setNote: (v: string) => void
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-[2fr_1.3fr_0.7fr]">
      <label className="space-y-1 text-sm">
        <span className="text-slate-600">Item</span>
        <input className={field} value={name} onChange={(e) => setName(e.target.value)} required maxLength={80} placeholder="Government photo ID" />
      </label>
      <label className="space-y-1 text-sm">
        <span className="text-slate-600">Category</span>
        <select className={field} value={category} onChange={(e) => setCategory(e.target.value as Category)}>
          {CATEGORIES.map((x) => <option key={x.key} value={x.key}>{x.emoji} {x.label}</option>)}
        </select>
      </label>
      <label className="space-y-1 text-sm">
        <span className="text-slate-600">Quantity</span>
        <input className={field} type="number" min={1} max={99} value={quantity}
          onChange={(e) => setQuantity(Math.min(99, Math.max(1, Number(e.target.value) || 1)))} />
      </label>
      <label className="space-y-1 text-sm sm:col-span-3">
        <span className="text-slate-600">Note for the traveller (optional)</span>
        <input className={field} value={note} onChange={(e) => setNote(e.target.value)} maxLength={200} placeholder="Hotels ask for it at check-in" />
      </label>
    </div>
  )
}

function CreateForm({ onDone }: { onDone: () => void }) {
  const create = useCreateDefault()
  const [name, setName] = useState('')
  const [category, setCategory] = useState<Category>('documents')
  const [quantity, setQuantity] = useState(1)
  const [note, setNote] = useState('')
  const [who, setWho] = useState<'everyone' | 'one'>('everyone')
  const [email, setEmail] = useState('')

  function submit(e: FormEvent) {
    e.preventDefault()
    create.mutate(
      {
        name, category, quantity, note: note.trim() || undefined,
        user_email: who === 'one' ? email.trim() : undefined,
      },
      { onSuccess: onDone },
    )
  }

  return (
    <form onSubmit={submit} className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
      <Fields {...{ name, setName, category, setCategory, quantity, setQuantity, note, setNote }} />
      <fieldset className="space-y-2 text-sm">
        <legend className="mb-1 text-slate-600">Add it to</legend>
        <label className="flex items-center gap-2">
          <input type="radio" checked={who === 'everyone'} onChange={() => setWho('everyone')} /> Every traveller’s packing lists
        </label>
        <label className="flex items-center gap-2">
          <input type="radio" checked={who === 'one'} onChange={() => setWho('one')} /> Only one traveller
        </label>
        {who === 'one' && (
          <input className={`${field} max-w-sm`} type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Their account email" />
        )}
      </fieldset>
      <ErrorNote error={create.error} fallback="Could not add the item." />
      <div className="flex gap-2">
        <Button type="submit" variant="primary" disabled={create.isPending}>{create.isPending ? 'Adding…' : 'Add item'}</Button>
        <Button onClick={onDone}>Cancel</Button>
      </div>
    </form>
  )
}

function EditForm({ d, onDone }: { d: PackingDefault; onDone: () => void }) {
  const update = useUpdateDefault()
  const [name, setName] = useState(d.name)
  const [category, setCategory] = useState<Category>(d.category)
  const [quantity, setQuantity] = useState(d.quantity)
  const [note, setNote] = useState(d.note ?? '')

  function submit(e: FormEvent) {
    e.preventDefault()
    update.mutate({ id: d.id, name, category, quantity, note: note.trim() || null }, { onSuccess: onDone })
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <Fields {...{ name, setName, category, setCategory, quantity, setQuantity, note, setNote }} />
      <p className="text-xs text-slate-500">
        Applies to {d.user_email ? `only ${d.user_email}` : 'everyone'}. Changes show on their lists straight away.
      </p>
      <ErrorNote error={update.error} fallback="Could not save it." />
      <div className="flex gap-2">
        <Button type="submit" variant="primary" disabled={update.isPending}>{update.isPending ? 'Saving…' : 'Save'}</Button>
        <Button onClick={onDone}>Cancel</Button>
      </div>
    </form>
  )
}
