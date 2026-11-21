import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { apiErrorMessage, useAuth } from '@/lib/auth'
import { Icon } from '@/components/Icon'
import { coverTone, mediaUrl } from '@/lib/media'
import { INR, fmtDate, useBookPackage, usePackage } from './api'

function isoIn(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

export function PackageDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: p, isPending, isError } = usePackage(id)
  const { isAuthenticated } = useAuth()

  if (isPending) return <div className="h-80 animate-pulse rounded-2xl bg-slate-200/60" />
  if (isError || !p) {
    return (
      <p className="text-sm text-slate-600">
        This package isn’t available. <Link to="/packages" className="underline">See all packages</Link>
      </p>
    )
  }

  return (
    <div className="space-y-8">
      <Link to="/packages" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900">
        <Icon name="back" className="h-4 w-4" /> All packages
      </Link>

      <div className="grid gap-8 lg:grid-cols-[1.6fr_1fr]">
        <div className="space-y-8">
          <header className={`relative flex min-h-[20rem] flex-col justify-end overflow-hidden rounded-2xl bg-gradient-to-br p-6 text-white sm:min-h-[26rem] sm:p-10 ${coverTone(p.title)}`}>
            {p.images?.[0] ? (
              <img src={mediaUrl(p.images[0])} alt="" className="absolute inset-0 h-full w-full object-cover" />
            ) : (
              <div aria-hidden className="absolute -top-24 -right-16 h-72 w-72 rounded-full bg-indigo-500/30 blur-3xl" />
            )}
            <div aria-hidden className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/35 to-black/10" />
            <p className="relative flex items-center gap-1.5 text-sm text-slate-300">
              <Icon name="pin" className="h-4 w-4" /> {p.destination}
            </p>
            <h1 className="font-display relative mt-2 text-4xl leading-tight tracking-tight sm:text-5xl">{p.title}</h1>
            <p className="relative mt-2 text-sm text-slate-400">
              by{' '}
              {p.business_slug ? (
                <Link to={`/b/${p.business_slug}`} className="font-medium text-white underline-offset-4 hover:underline">
                  {p.business_name}
                </Link>
              ) : (
                <span className="font-medium text-white">Safarnama</span>
              )}
            </p>
            {p.summary && <p className="relative mt-3 max-w-2xl text-slate-300">{p.summary}</p>}
            <div className="relative mt-6 flex flex-wrap gap-2 text-sm">
              <Chip>{p.duration_days} days</Chip>
              <Chip>{INR.format(p.price_per_person)} per person</Chip>
              {p.seats_left != null && <Chip>{p.seats_left} seats left</Chip>}
              {p.style_tags.map((t) => <Chip key={t}>{t}</Chip>)}
            </div>
          </header>

          {p.images && p.images.length > 1 && <Gallery images={p.images} title={p.title} />}

          {p.description && (
            <section>
              <h2 className="text-lg font-semibold">About this trip</h2>
              <p className="mt-2 whitespace-pre-line leading-relaxed text-slate-600">{p.description}</p>
            </section>
          )}

          {p.highlights.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold">Itinerary highlights</h2>
              <ol className="relative mt-4 space-y-4 border-l border-slate-200 pl-6">
                {p.highlights.map((h, i) => (
                  <li key={i} className="relative">
                    <span className="absolute top-1 -left-[31px] flex h-3.5 w-3.5 items-center justify-center rounded-full border-2 border-white bg-indigo-600 ring-1 ring-indigo-200" />
                    <p className="text-slate-700">{h}</p>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {p.inclusions.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold">What’s included</h2>
              <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                {p.inclusions.map((i) => (
                  <li key={i} className="flex items-center gap-2.5 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm">
                    <Icon name="check" className="h-4 w-4 text-emerald-600" /> {i}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          {isAuthenticated ? (
            <BookingForm id={p.id} price={p.price_per_person} days={p.duration_days} seatsLeft={p.seats_left}
              validFrom={p.valid_from} validUntil={p.valid_until} />
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-lg font-semibold">{INR.format(p.price_per_person)} <span className="text-sm font-normal text-slate-500">/ person</span></p>
              <p className="mt-2 text-sm text-slate-600">Log in to choose your dates and opt into this package.</p>
              <Link to="/login" state={{ from: `/packages/${p.id}` }} className="mt-5 flex w-full items-center justify-center rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800">
                Log in to book
              </Link>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}

function Chip({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full bg-white/10 px-3 py-1 capitalize ring-1 ring-white/15">{children}</span>
}

function BookingForm({
  id, price, days, seatsLeft, validFrom, validUntil,
}: {
  id: string; price: number; days: number; seatsLeft: number | null; validFrom: string | null; validUntil: string | null
}) {
  const book = useBookPackage(id)
  const navigate = useNavigate()
  const minDate = validFrom && validFrom > isoIn(1) ? validFrom : isoIn(1)
  const [start, setStart] = useState(minDate)
  const [travelers, setTravelers] = useState(2)
  const [note, setNote] = useState('')
  const [done, setDone] = useState(false)
  const maxTravellers = Math.min(20, seatsLeft ?? 20)
  const end = (() => {
    const d = new Date(`${start}T00:00:00`)
    d.setDate(d.getDate() + days - 1)
    return d.toISOString().slice(0, 10)
  })()

  function submit(e: FormEvent) {
    e.preventDefault()
    book.mutate({ travelers, start_date: start, note: note.trim() || undefined }, { onSuccess: () => setDone(true) })
  }

  if (done) {
    return (
      <div className="rounded-2xl border border-emerald-200 bg-white p-6 shadow-sm">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200">
          <Icon name="check" className="h-5 w-5" />
        </span>
        <p className="mt-4 text-lg font-semibold">You’re in</p>
        <p className="mt-1 text-sm text-slate-600">
          Request sent for {fmtDate(start)}. We’ll confirm it shortly — you can track it under My bookings.
        </p>
        <button onClick={() => navigate('/packages')} className="mt-5 w-full rounded-xl border border-slate-200 px-4 py-3 text-sm font-medium hover:bg-slate-50">
          Back to packages
        </button>
      </div>
    )
  }

  if (seatsLeft === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm">
        This package is sold out.
      </div>
    )
  }

  const input = 'w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-slate-900'
  return (
    <form onSubmit={submit} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-2xl font-semibold tracking-tight">
        {INR.format(price)} <span className="text-sm font-normal text-slate-500">/ person</span>
      </p>
      <label className="block space-y-1.5 text-sm">
        <span className="font-medium text-slate-800">Start date</span>
        <input type="date" required className={input} min={minDate} max={validUntil ?? undefined} value={start} onChange={(e) => setStart(e.target.value)} />
        <span className="block text-xs text-slate-500">Returns {fmtDate(end)}</span>
      </label>
      <label className="block space-y-1.5 text-sm">
        <span className="font-medium text-slate-800">Travellers</span>
        <input type="number" min={1} max={maxTravellers} required className={input} value={travelers} onChange={(e) => setTravelers(Number(e.target.value))} />
      </label>
      <label className="block space-y-1.5 text-sm">
        <span className="flex justify-between font-medium text-slate-800">Note <span className="text-xs font-normal text-slate-400">Optional</span></span>
        <textarea rows={2} maxLength={500} className={input} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Dietary needs, room preference…" />
      </label>
      <div className="flex items-center justify-between border-t border-slate-100 pt-4 text-sm">
        <span className="text-slate-600">Total</span>
        <span className="text-lg font-semibold tabular-nums">{INR.format(price * (travelers || 0))}</span>
      </div>
      {book.error != null && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
          {apiErrorMessage(book.error, 'Could not book this package.')}
        </p>
      )}
      <button type="submit" disabled={book.isPending} className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50">
        {book.isPending ? 'Sending…' : 'Opt into this package'}
        <Icon name="arrow" className="h-4 w-4" />
      </button>
      <p className="text-center text-xs text-slate-500">No payment now — the team confirms availability first.</p>
    </form>
  )
}

function Gallery({ images, title }: { images: string[]; title: string }) {
  const [open, setOpen] = useState<number | null>(null)
  return (
    <section>
      <h2 className="text-lg font-semibold">Photos</h2>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {images.map((url, i) => (
          <button
            key={url}
            type="button"
            onClick={() => setOpen(i)}
            className="group aspect-[4/3] overflow-hidden rounded-xl bg-slate-100"
          >
            <img src={mediaUrl(url)} alt={`${title} photo ${i + 1}`} loading="lazy" className="h-full w-full object-cover transition group-hover:scale-105" />
          </button>
        ))}
      </div>
      {open != null && (
        <div className="fixed inset-0 z-[1500] flex items-center justify-center bg-black/90 p-4" onClick={() => setOpen(null)}>
          <img src={mediaUrl(images[open])} alt="" className="max-h-[85vh] max-w-full rounded-lg object-contain" />
          <button
            type="button"
            aria-label="Close"
            onClick={() => setOpen(null)}
            className="absolute top-4 right-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
          >
            <Icon name="close" className="h-5 w-5" />
          </button>
          {images.length > 1 && (
            <>
              <button
                type="button"
                aria-label="Previous"
                onClick={(e) => { e.stopPropagation(); setOpen((open - 1 + images.length) % images.length) }}
                className="absolute left-4 rounded-full bg-white/10 p-3 text-white hover:bg-white/20"
              >
                <Icon name="back" className="h-5 w-5" />
              </button>
              <button
                type="button"
                aria-label="Next"
                onClick={(e) => { e.stopPropagation(); setOpen((open + 1) % images.length) }}
                className="absolute right-4 rounded-full bg-white/10 p-3 text-white hover:bg-white/20"
              >
                <Icon name="arrow" className="h-5 w-5" />
              </button>
            </>
          )}
        </div>
      )}
    </section>
  )
}
