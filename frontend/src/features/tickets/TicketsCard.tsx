import { useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { apiErrorMessage } from '@/lib/auth'
import { Icon, type IconName } from '@/components/Icon'
import { useTrips } from '@/features/trips/api'

type Mode = 'train' | 'flight' | 'bus' | 'hotel' | 'other'

interface Ticket {
  id: string
  mode: Mode
  provider: string | null
  number: string | null
  pnr: string | null
  from_place: string | null
  to_place: string | null
  depart_at: string | null
  arrive_at: string | null
  seat: string | null
  travel_class: string | null
  passengers: number
  fare: number | null
  notes: string | null
  status: string | null
  status_checked_at: string | null
  has_file: boolean
  file_type: string | null
  trip_id: string | null
  trip_destination: string | null
}

/** Field labels change with the kind of ticket, so the form reads like the ticket in your hand. */
const MODES: Record<Mode, {
  label: string; icon: IconName; provider: string; number: string; pnr: string; pnrHint: string
  from: string; to: string | null; depart: string; arrive: string; seat: string; cls: string
  classes?: string[]; people: string
}> = {
  train: {
    label: 'Train', icon: 'train', provider: 'Train name', number: 'Train no.', pnr: 'PNR', pnrHint: '10 digits',
    from: 'From station', to: 'To station', depart: 'Departure', arrive: 'Arrival', seat: 'Coach / berth', cls: 'Class',
    classes: ['SL', '3A', '3E', '2A', '1A', 'CC', 'EC', '2S'], people: 'Passengers',
  },
  flight: {
    label: 'Flight', icon: 'plane', provider: 'Airline', number: 'Flight no.', pnr: 'PNR / booking ref', pnrHint: '6 letters & numbers',
    from: 'From airport', to: 'To airport', depart: 'Departure', arrive: 'Arrival', seat: 'Seat / gate', cls: 'Class',
    classes: ['Economy', 'Premium economy', 'Business', 'First'], people: 'Passengers',
  },
  bus: {
    label: 'Bus', icon: 'bus', provider: 'Operator', number: 'Bus no.', pnr: 'Ticket / PNR no.', pnrHint: 'As printed on the ticket',
    from: 'Boarding point', to: 'Drop point', depart: 'Departure', arrive: 'Arrival', seat: 'Seat no.', cls: 'Bus type',
    classes: ['Sleeper', 'AC Sleeper', 'Seater', 'AC Seater', 'Volvo'], people: 'Passengers',
  },
  hotel: {
    label: 'Hotel', icon: 'bed', provider: 'Hotel name', number: 'Room type', pnr: 'Booking ID', pnrHint: 'From the confirmation',
    from: 'City / address', to: null, depart: 'Check-in', arrive: 'Check-out', seat: 'Room no.', cls: 'Plan',
    classes: ['Room only', 'With breakfast', 'All meals'], people: 'Guests',
  },
  other: {
    label: 'Other', icon: 'file', provider: 'Company', number: 'Number', pnr: 'Reference', pnrHint: 'Booking reference',
    from: 'From', to: 'To', depart: 'Starts', arrive: 'Ends', seat: 'Seat', cls: 'Class', people: 'People',
  },
}

const PNR_PAGE = 'https://www.indianrail.gov.in/enquiry/PNR/PnrEnquiry.html'

const fmt = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : null

/**
 * My tickets: bookings made anywhere (IRCTC, an airline, redBus, a hotel
 * site), saved in one place. On the profile it lists them all; on a trip
 * page (`tripId`) only that trip's, and new ones are linked to it.
 */
export function TicketsCard({ tripId, title = 'My tickets' }: { tripId?: string; title?: string }) {
  const key = ['my-tickets', tripId ?? 'all']
  const q = useQuery({
    queryKey: key,
    queryFn: async () =>
      (await api.get<{ enabled: boolean; live_pnr: boolean; items: Ticket[] }>('/me/tickets', { params: tripId ? { trip_id: tripId } : {} })).data,
  })
  const [adding, setAdding] = useState(false)
  const [tab, setTab] = useState<'upcoming' | 'past'>('upcoming')

  const items = q.data?.items ?? []
  const now = Date.now()
  const isPast = (t: Ticket) => {
    const end = t.arrive_at ?? t.depart_at
    return end !== null && new Date(end).getTime() < now - 6 * 3600_000
  }
  const shown = items.filter((t) => (tab === 'past' ? isPast(t) : !isPast(t)))
  if (tab === 'past') shown.reverse()
  const pastCount = items.filter(isPast).length

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 px-6 py-5 sm:px-8">
        <div>
          <h2 className="text-lg font-semibold">{title}</h2>
          <p className="mt-0.5 max-w-xl text-sm text-slate-500">
            Booked somewhere else? Save the train, flight, bus or hotel here with its PNR and e-ticket, so everything is in one place.
          </p>
        </div>
        {q.data?.enabled !== false && (
          <button
            onClick={() => setAdding((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-xl bg-[#1C2452] px-4 py-2 text-sm font-semibold text-white hover:bg-[#283372]"
          >
            <Icon name={adding ? 'close' : 'plus'} className="h-4 w-4" /> {adding ? 'Close' : 'Add ticket'}
          </button>
        )}
      </div>

      <div className="space-y-4 px-6 py-6 sm:px-8">
        {q.data && !q.data.enabled && (
          <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Saving tickets isn’t switched on yet. The site owner needs to set DOCUMENT_ENCRYPTION_KEY.
          </p>
        )}
        {adding && <TicketForm tripId={tripId} onDone={() => setAdding(false)} queryKey={key} />}

        {items.length > 0 && (
          <div className="inline-flex rounded-lg bg-slate-100 p-1 text-sm">
            {(['upcoming', 'past'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`rounded-md px-3 py-1 ${tab === t ? 'bg-white font-medium shadow-sm' : 'text-slate-600'}`}
              >
                {t === 'upcoming' ? `Upcoming (${items.length - pastCount})` : `Past (${pastCount})`}
              </button>
            ))}
          </div>
        )}

        {q.isPending && <p className="text-sm text-slate-500">Loading…</p>}
        {q.data?.enabled && items.length === 0 && !adding && (
          <p className="rounded-xl border border-dashed border-slate-300 px-5 py-8 text-center text-sm text-slate-500">
            No tickets yet. Add your first one — just the PNR is enough to start.
          </p>
        )}
        <div className="space-y-3">
          {shown.map((t) => <TicketStub key={t.id} t={t} queryKey={key} livePnr={q.data?.live_pnr ?? false} tripId={tripId} />)}
        </div>
        {items.length > 0 && shown.length === 0 && (
          <p className="text-sm text-slate-500">{tab === 'upcoming' ? 'Nothing coming up.' : 'No past tickets.'}</p>
        )}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------- one ticket

function TicketStub({ t, queryKey, livePnr, tripId }: { t: Ticket; queryKey: unknown[]; livePnr: boolean; tripId?: string }) {
  const qc = useQueryClient()
  const m = MODES[t.mode]
  const [editing, setEditing] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const refresh = () => qc.invalidateQueries({ queryKey: ['my-tickets'] })

  const del = useMutation({ mutationFn: async () => api.delete(`/me/tickets/${t.id}`), onSuccess: refresh })
  const status = useMutation({
    mutationFn: async () =>
      (await api.post<{ status: string | null; live: boolean; enquiry_url: string; message: string | null }>(`/me/tickets/${t.id}/pnr-status`)).data,
    onSuccess: (r) => {
      if (r.live) void refresh()
      else {
        setMsg(r.message)
        window.open(r.enquiry_url, '_blank', 'noopener,noreferrer')
      }
    },
    onError: (e) => setMsg(apiErrorMessage(e, 'Could not check the PNR.')),
  })

  async function openFile() {
    const tab = window.open('', '_blank')
    try {
      const res = await api.get<Blob>(`/me/tickets/${t.id}/file`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      if (tab) tab.location.href = url
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (e) {
      tab?.close()
      setMsg(apiErrorMessage(e, 'Could not open the e-ticket.'))
    }
  }

  async function copyPnr() {
    if (!t.pnr) return
    try {
      await navigator.clipboard.writeText(t.pnr)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard blocked */
    }
  }

  if (editing) return <TicketForm existing={t} tripId={tripId} queryKey={queryKey} onDone={() => setEditing(false)} />

  const heading = [t.provider, t.number].filter(Boolean).join(' ') || m.label
  return (
    <article className="flex flex-col overflow-hidden rounded-2xl bg-[#1C2452] text-white sm:flex-row">
      <div className="flex-1 p-5">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/10">
            <Icon name={m.icon} className="h-5 w-5 text-[#F2A93B]" />
          </span>
          <div className="min-w-0">
            <p className="truncate font-semibold">{heading}</p>
            {(t.from_place || t.to_place) && (
              <p className="mt-0.5 text-sm text-white/80">
                {t.from_place ?? '—'}
                {m.to && <> <span className="text-[#F2A93B]">→</span> {t.to_place ?? '—'}</>}
              </p>
            )}
          </div>
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
          {t.depart_at && <Fact label={m.depart} value={fmt(t.depart_at)!} />}
          {t.arrive_at && <Fact label={m.arrive} value={fmt(t.arrive_at)!} />}
          {t.seat && <Fact label={m.seat} value={t.seat} />}
          {t.travel_class && <Fact label={m.cls} value={t.travel_class} />}
          <Fact label={m.people} value={String(t.passengers)} />
          {t.fare !== null && <Fact label="Fare" value={`₹${Math.round(t.fare).toLocaleString('en-IN')}`} />}
        </dl>
        {t.trip_destination && !tripId && (
          <p className="mt-3 text-xs text-white/60">For your trip to {t.trip_destination.split(',')[0]}</p>
        )}
        {t.notes && <p className="mt-2 text-xs text-white/60">{t.notes}</p>}
      </div>

      {/* stub */}
      <div className="flex flex-col justify-between gap-3 border-t-2 border-dashed border-white/15 p-5 sm:w-60 sm:border-t-0 sm:border-l-2">
        <div>
          <p className="text-xs text-white/55">{m.pnr}</p>
          {t.pnr ? (
            <button onClick={copyPnr} className="font-mono text-xl tracking-wider text-[#F2A93B] hover:underline" title="Copy">
              {t.pnr}
            </button>
          ) : (
            <p className="text-sm text-white/50">Not added</p>
          )}
          {copied && <span className="ml-2 text-xs text-white/70">Copied</span>}
          {t.mode === 'train' && t.status && (
            <p className="mt-1 text-xs text-emerald-200">{t.status}</p>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5 text-xs">
          {t.mode === 'train' && t.pnr && (
            <button
              onClick={() => { setMsg(null); status.mutate() }}
              disabled={status.isPending}
              className="rounded-lg bg-[#F2A93B] px-2.5 py-1.5 font-semibold text-[#1C2452] disabled:opacity-60"
              title={livePnr ? 'Check the live PNR status' : 'Opens the official PNR enquiry page'}
            >
              {status.isPending ? 'Checking…' : 'PNR status'}
            </button>
          )}
          {t.has_file && (
            <button onClick={openFile} className="rounded-lg bg-white/10 px-2.5 py-1.5 hover:bg-white/20">E-ticket</button>
          )}
          <button onClick={() => setEditing(true)} className="rounded-lg px-2 py-1.5 text-white/70 hover:text-white">Edit</button>
          {confirm ? (
            <>
              <button onClick={() => del.mutate()} className="rounded-lg bg-red-500 px-2.5 py-1.5 font-medium">Delete</button>
              <button onClick={() => setConfirm(false)} className="px-1.5 text-white/70">Cancel</button>
            </>
          ) : (
            <button onClick={() => setConfirm(true)} className="rounded-lg px-2 py-1.5 text-white/50 hover:text-red-300">Remove</button>
          )}
        </div>
        {msg && (
          <p className="text-xs text-white/70">
            {msg}{' '}
            {t.mode === 'train' && <a href={PNR_PAGE} target="_blank" rel="noopener noreferrer" className="underline">Open</a>}
          </p>
        )}
      </div>
    </article>
  )
}

/** A labelled form field. Defined out here, not inside the form, so typing
 *  never remounts the input and drops focus. */
function L({ label, children, wide }: { label: string; children: ReactNode; wide?: boolean }) {
  return (
    <label className={`space-y-1 text-sm ${wide ? 'sm:col-span-2' : ''}`}>
      <span className="text-slate-600">{label}</span>
      {children}
    </label>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-white/55">{label}</dt>
      <dd className="truncate">{value}</dd>
    </div>
  )
}

// ---------------------------------------------------------------- the form

function TicketForm({
  existing, tripId, queryKey, onDone,
}: { existing?: Ticket; tripId?: string; queryKey: unknown[]; onDone: () => void }) {
  const qc = useQueryClient()
  const { data: trips = [] } = useTrips()
  const fileRef = useRef<HTMLInputElement>(null)
  const [mode, setMode] = useState<Mode>(existing?.mode ?? 'train')
  const m = MODES[mode]
  const local = (iso: string | null | undefined) => (iso ? iso.slice(0, 16) : '')
  const [f, setF] = useState({
    provider: existing?.provider ?? '', number: existing?.number ?? '', pnr: existing?.pnr ?? '',
    from_place: existing?.from_place ?? '', to_place: existing?.to_place ?? '',
    depart_at: local(existing?.depart_at), arrive_at: local(existing?.arrive_at),
    seat: existing?.seat ?? '', travel_class: existing?.travel_class ?? '',
    passengers: String(existing?.passengers ?? 1), fare: existing?.fare != null ? String(existing.fare) : '',
    notes: existing?.notes ?? '', trip_id: existing?.trip_id ?? tripId ?? '',
  })
  const [fileName, setFileName] = useState<string | null>(null)
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((x) => ({ ...x, [k]: e.target.value }))

  // Suggest the trip whose dates hold the departure, when none is chosen.
  const suggested = useMemo(() => {
    if (f.trip_id || !f.depart_at) return null
    const d = f.depart_at.slice(0, 10)
    return trips.find((t) => t.start_date <= d && d <= t.end_date) ?? null
  }, [f.trip_id, f.depart_at, trips])

  const save = useMutation({
    mutationFn: async () => {
      const form = new FormData()
      form.append('mode', mode)
      for (const [k, v] of Object.entries(f)) {
        if (k === 'trip_id') continue
        if (v.trim() !== '') form.append(k, v.trim())
      }
      if (f.trip_id) form.append('trip_id', f.trip_id)
      else if (existing?.trip_id) form.append('trip_id', 'none')
      const file = fileRef.current?.files?.[0]
      if (file) form.append('file', file)
      const cfg = { headers: { 'Content-Type': 'multipart/form-data' } }
      return existing
        ? (await api.put<Ticket>(`/me/tickets/${existing.id}`, form, cfg)).data
        : (await api.post<Ticket>('/me/tickets', form, cfg)).data
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['my-tickets'] })
      void qc.invalidateQueries({ queryKey })
      onDone()
    },
  })

  function submit(e: FormEvent) {
    e.preventDefault()
    save.mutate()
  }

  const field = 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-900'
  return (
    <form onSubmit={submit} className="space-y-4 rounded-2xl border border-slate-300 bg-slate-50 p-5">
      {!existing && (
        <div className="inline-flex flex-wrap rounded-xl bg-white p-1 ring-1 ring-slate-200">
          {(Object.keys(MODES) as Mode[]).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setMode(k)}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm ${
                mode === k ? 'bg-[#1C2452] font-medium text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Icon name={MODES[k].icon} className="h-4 w-4" /> {MODES[k].label}
            </button>
          ))}
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-4">
        <L label={m.pnr}>
          <input className={`${field} font-mono uppercase`} value={f.pnr} onChange={set('pnr')} placeholder={m.pnrHint} maxLength={30} autoComplete="off" />
        </L>
        <L label={m.provider}>
          <input className={field} value={f.provider} onChange={set('provider')} maxLength={80} />
        </L>
        <L label={m.number}>
          <input className={field} value={f.number} onChange={set('number')} maxLength={30} placeholder={mode === 'train' ? '12951' : mode === 'flight' ? '6E 2134' : ''} />
        </L>
        <L label={m.cls}>
          <input className={field} value={f.travel_class} onChange={set('travel_class')} list={`classes-${mode}`} maxLength={30} />
          {m.classes && (
            <datalist id={`classes-${mode}`}>
              {m.classes.map((c) => <option key={c} value={c} />)}
            </datalist>
          )}
        </L>
        <L label={m.from} wide={!m.to}>
          <input className={field} value={f.from_place} onChange={set('from_place')} maxLength={120} />
        </L>
        {m.to && (
          <L label={m.to}>
            <input className={field} value={f.to_place} onChange={set('to_place')} maxLength={120} />
          </L>
        )}
        <L label={m.depart}>
          <input className={field} type="datetime-local" value={f.depart_at} onChange={set('depart_at')} />
        </L>
        <L label={m.arrive}>
          <input className={field} type="datetime-local" value={f.arrive_at} onChange={set('arrive_at')} min={f.depart_at || undefined} />
        </L>
        <L label={m.seat}>
          <input className={field} value={f.seat} onChange={set('seat')} maxLength={60} />
        </L>
        <L label={m.people}>
          <input className={field} type="number" min={1} max={50} value={f.passengers} onChange={set('passengers')} />
        </L>
        <L label="Fare paid (₹)">
          <input className={field} type="number" min={0} value={f.fare} onChange={set('fare')} />
        </L>
        {!tripId && (
          <L label="For trip (optional)">
            <select className={field} value={f.trip_id} onChange={set('trip_id')}>
              <option value="">No trip</option>
              {trips.map((t) => <option key={t.id} value={t.id}>{t.destination.split(',')[0]} ({t.start_date})</option>)}
            </select>
          </L>
        )}
        <L label="Notes (optional)" wide>
          <input className={field} value={f.notes} onChange={set('notes')} maxLength={1000} placeholder="e.g. Reach 2 hours early, terminal 1" />
        </L>
        <div className="space-y-1 text-sm sm:col-span-2">
          <span className="text-slate-600">{existing?.has_file ? 'Replace the e-ticket (optional)' : 'E-ticket — PDF or photo (optional)'}</span>
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => fileRef.current?.click()} className="rounded-lg border border-slate-300 bg-white px-3 py-2 font-medium text-slate-700 hover:bg-slate-100">
              Choose file
            </button>
            <span className="truncate text-slate-500">{fileName ?? 'No file chosen'}</span>
            <input ref={fileRef} type="file" accept="application/pdf,image/jpeg,image/png,image/webp" className="sr-only"
              onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)} />
          </div>
        </div>
      </div>

      {suggested && (
        <p className="text-sm text-slate-600">
          This looks like your trip to {suggested.destination.split(',')[0]}.{' '}
          <button type="button" onClick={() => setF((x) => ({ ...x, trip_id: suggested.id }))} className="font-medium text-[#1C2452] underline">
            Link it
          </button>
        </p>
      )}
      {save.isError && <p className="text-sm text-red-600">{apiErrorMessage(save.error, 'Could not save the ticket.')}</p>}
      <div className="flex gap-2">
        <button type="submit" disabled={save.isPending} className="rounded-lg bg-[#1C2452] px-4 py-2 text-sm font-semibold text-white hover:bg-[#283372] disabled:opacity-50">
          {save.isPending ? 'Saving…' : existing ? 'Save changes' : 'Save ticket'}
        </button>
        <button type="button" onClick={onDone} className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:text-slate-900">Cancel</button>
      </div>
    </form>
  )
}
