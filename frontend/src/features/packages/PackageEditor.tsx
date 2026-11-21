import { useState } from 'react'
import { api } from '@/lib/api'
import { apiErrorMessage } from '@/lib/auth'
import { Button, ErrorNote } from '@/features/admin/ui'
import type { PackageInput, TravelPackage } from '@/features/admin/types'
import { ImageManager } from '@/features/packages/ImageManager'

const TAGS = ['adventure', 'relax', 'culture', 'food', 'nature', 'spiritual', 'shopping', 'nightlife'] as const

export const EMPTY_PACKAGE: PackageInput = {
  title: '', destination: '', duration_days: 4, price_per_person: 15000, summary: '', description: '',
  inclusions: [], highlights: [], style_tags: [], images: [], seats: null, valid_from: null, valid_until: null, is_active: true,
}

function lines(text: string): string[] {
  return text.split('\n').map((l) => l.trim()).filter(Boolean)
}

export function PackageEditor({
  pkg,
  busy,
  error,
  onSubmit,
  onCancel,
  fillPath,
}: {
  pkg: TravelPackage | null
  busy: boolean
  error: unknown
  onSubmit: (payload: PackageInput) => void
  onCancel: () => void
  /** Where to ask for AI suggestions for blank fields (business or admin). */
  fillPath?: string
}) {
  const init: PackageInput = pkg
    ? {
        title: pkg.title, destination: pkg.destination, duration_days: pkg.duration_days,
        price_per_person: pkg.price_per_person, summary: pkg.summary, description: pkg.description,
        inclusions: pkg.inclusions, highlights: pkg.highlights, style_tags: pkg.style_tags,
        images: pkg.images ?? [], seats: pkg.seats,
        valid_from: pkg.valid_from, valid_until: pkg.valid_until, is_active: pkg.is_active,
      }
    : EMPTY_PACKAGE
  const [f, setF] = useState(init)
  const [inclusions, setInclusions] = useState(init.inclusions.join('\n'))
  const [highlights, setHighlights] = useState(init.highlights.join('\n'))
  const [filling, setFilling] = useState(false)
  const [fillNote, setFillNote] = useState<string | null>(null)
  const [undo, setUndo] = useState<{ f: PackageInput; inclusions: string; highlights: string } | null>(null)

  /** Fill only what is still blank; anything already written stays exactly as it is. */
  async function fillBlanks() {
    if (!fillPath) return
    if (f.destination.trim().length < 2) return setFillNote('Add the destination, length and price first.')
    setFilling(true)
    setFillNote(null)
    try {
      const { data } = await api.post<{ fields: Partial<PackageInput>; filled: string[]; source: string }>(fillPath, {
        title: f.title, destination: f.destination.trim(), duration_days: f.duration_days, price_per_person: f.price_per_person,
        summary: f.summary, description: f.description, inclusions: lines(inclusions), highlights: lines(highlights),
        style_tags: f.style_tags,
      })
      const x = data.fields
      setUndo({ f, inclusions, highlights })
      setF((cur) => ({
        ...cur,
        title: x.title ?? cur.title,
        summary: x.summary ?? cur.summary,
        description: x.description ?? cur.description,
        style_tags: x.style_tags ?? cur.style_tags,
      }))
      if (x.inclusions) setInclusions(x.inclusions.join('\n'))
      if (x.highlights) setHighlights(x.highlights.join('\n'))
      const names: Record<string, string> = { title: 'title', summary: 'summary', description: 'description', inclusions: "what's included", highlights: 'day-by-day', style_tags: 'style' }
      setFillNote(
        data.filled.length
          ? `Filled ${data.filled.map((k) => names[k] ?? k).join(', ')}${data.source === 'ai' ? ' with AI' : ' from our travel lists (AI not connected)'}. Check and edit before saving.`
          : 'Everything is already filled in.',
      )
    } catch (err) {
      setFillNote(apiErrorMessage(err, 'Could not fill the package.'))
    } finally {
      setFilling(false)
    }
  }

  const input = 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-900'
  const label = 'space-y-1 text-sm'
  const cap = 'text-xs font-medium text-slate-600'

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit({
          ...f,
          title: f.title.trim(),
          destination: f.destination.trim(),
          inclusions: lines(inclusions),
          highlights: lines(highlights),
          valid_from: f.valid_from || null,
          valid_until: f.valid_until || null,
        })
      }}
      className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
    >
      <h2 className="text-base font-semibold">{pkg ? `Edit “${pkg.title}”` : 'New package'}</h2>
      <ImageManager images={f.images} onChange={(images) => setF((cur) => ({ ...cur, images }))} />
      {fillPath && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-indigo-100 bg-indigo-50/60 px-4 py-3">
          <button type="button" onClick={fillBlanks} disabled={filling}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
            {filling ? 'Filling…' : '✨ Fill blanks with AI'}
          </button>
          <span className="flex-1 text-sm text-slate-600">
            {fillNote ?? "Enter the destination, days and price. AI writes whatever you leave blank — title, summary, what's included (AC car, breakfast…), day-by-day and style. What you wrote stays."}
          </span>
          {undo && (
            <button type="button" onClick={() => { setF(undo.f); setInclusions(undo.inclusions); setHighlights(undo.highlights); setUndo(null); setFillNote(null) }}
              className="text-sm font-medium text-indigo-700 hover:underline">
              Undo
            </button>
          )}
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <label className={label}>
          <span className={cap}>Title</span>
          <input className={input} required minLength={3} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="Golden Triangle Classic" />
        </label>
        <label className={label}>
          <span className={cap}>Destination</span>
          <input className={input} required minLength={2} value={f.destination} onChange={(e) => setF({ ...f, destination: e.target.value })} placeholder="Delhi, Agra, Jaipur" />
        </label>
        <label className={label}>
          <span className={cap}>Duration (days)</span>
          <input type="number" min={1} max={60} className={input} required value={f.duration_days} onChange={(e) => setF({ ...f, duration_days: Number(e.target.value) })} />
        </label>
        <label className={label}>
          <span className={cap}>Price per person (₹)</span>
          <input type="number" min={1} className={input} required value={f.price_per_person} onChange={(e) => setF({ ...f, price_per_person: Number(e.target.value) })} />
        </label>
        <label className={label}>
          <span className={cap}>Seats (blank = unlimited)</span>
          <input type="number" min={1} className={input} value={f.seats ?? ''} onChange={(e) => setF({ ...f, seats: e.target.value ? Number(e.target.value) : null })} />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className={label}>
            <span className={cap}>Available from</span>
            <input type="date" className={input} value={f.valid_from ?? ''} onChange={(e) => setF({ ...f, valid_from: e.target.value || null })} />
          </label>
          <label className={label}>
            <span className={cap}>Available until</span>
            <input type="date" className={input} value={f.valid_until ?? ''} onChange={(e) => setF({ ...f, valid_until: e.target.value || null })} />
          </label>
        </div>
        <label className={`${label} sm:col-span-2`}>
          <span className={cap}>Short summary (shown on the card)</span>
          <input className={input} maxLength={300} value={f.summary} onChange={(e) => setF({ ...f, summary: e.target.value })} placeholder="Forts, palaces and the Taj in five unhurried days." />
        </label>
        <label className={`${label} sm:col-span-2`}>
          <span className={cap}>Description</span>
          <textarea rows={4} className={input} maxLength={5000} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} />
        </label>
        <label className={label}>
          <span className={cap}>What’s included (one per line)</span>
          <textarea rows={5} className={input} value={inclusions} onChange={(e) => setInclusions(e.target.value)} placeholder={'Hotels (twin sharing)\nDaily breakfast\nAC cab with driver'} />
        </label>
        <label className={label}>
          <span className={cap}>Day-by-day highlights (one per line)</span>
          <textarea rows={5} className={input} value={highlights} onChange={(e) => setHighlights(e.target.value)} placeholder={'Day 1: Arrive in Delhi, Old Delhi food walk\nDay 2: Taj Mahal at sunrise'} />
        </label>
      </div>
      <fieldset>
        <legend className={`mb-2 ${cap}`}>Style</legend>
        <div className="flex flex-wrap gap-1.5">
          {TAGS.map((t) => {
            const on = f.style_tags.includes(t)
            return (
              <button
                key={t}
                type="button"
                onClick={() => setF({ ...f, style_tags: on ? f.style_tags.filter((x) => x !== t) : [...f.style_tags, t] })}
                className={`rounded-full border px-3 py-1 text-xs capitalize ${on ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 text-slate-600'}`}
              >
                {t}
              </button>
            )
          })}
        </div>
      </fieldset>
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input type="checkbox" checked={f.is_active} onChange={(e) => setF({ ...f, is_active: e.target.checked })} />
        Published — visible to every traveller
      </label>
      <ErrorNote error={error} fallback="Could not save the package." />
      <div className="flex gap-2">
        <Button type="submit" variant="primary" disabled={busy}>
          {busy ? 'Saving…' : pkg ? 'Save changes' : 'Create package'}
        </Button>
        <Button onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  )
}
