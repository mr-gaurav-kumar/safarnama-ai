import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { Icon } from '@/components/Icon'
import {
  formatDay, formatWhen, useCreateTripForUser, useDeleteTrip, useDeleteUser, useReplanTrip, useUpdateTrip,
  useUpdateUser, useUserDetail,
} from './api'
import { Badge, Button, ConfirmButton, ErrorNote } from './ui'
import type { AdminTripDetail, PlanStatus, TripStatus, UserUpdate } from './types'
import { EMPTY_TRIP, TripForm } from './TripForm'

const GENDER_LABEL: Record<string, string> = {
  male: 'Male', female: 'Female', other: 'Other', prefer_not: 'Prefer not to say',
}

const INR = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

function ageOf(dob: string): number {
  const b = new Date(`${dob}T00:00:00`)
  const t = new Date()
  let a = t.getFullYear() - b.getFullYear()
  if (t.getMonth() < b.getMonth() || (t.getMonth() === b.getMonth() && t.getDate() < b.getDate())) a--
  return a
}

/** Slide-over with everything about one account, and every action on it. */
export function UserDrawer({ userId, onClose }: { userId: string; onClose: () => void }) {
  const { user: me } = useAuth()
  const { data: u, isPending, isError } = useUserDetail(userId)
  const update = useUpdateUser()
  const remove = useDeleteUser()
  const [editing, setEditing] = useState(false)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const isSelf = me?.id === userId
  const busy = update.isPending || remove.isPending
  const patch = (p: UserUpdate) => update.mutate({ id: userId, patch: p })

  return (
    <div className="fixed inset-0 z-[1400] flex justify-end">
      <button aria-label="Close" onClick={onClose} className="absolute inset-0 bg-slate-950/30 backdrop-blur-[2px]" />
      <aside className="relative flex h-full w-full max-w-xl flex-col overflow-hidden bg-white shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
          {u ? (
            <div className="flex items-center gap-4">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-950 text-base font-semibold text-white">
                {u.name.split(/\s+/).map((p) => p[0]).join('').slice(0, 2).toUpperCase()}
              </span>
              <div>
                <p className="text-lg font-semibold">{u.name}</p>
                <p className="text-sm text-slate-500">{u.email}</p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  <Badge tone={u.role === 'admin' ? 'info' : 'neutral'}>{u.role}</Badge>
                  <Badge tone={u.is_verified ? 'good' : 'warn'}>{u.is_verified ? 'verified' : 'unverified'}</Badge>
                  {u.is_blocked && <Badge tone="bad">blocked</Badge>}
                  {u.open_flags > 0 && <Badge tone="warn">{u.open_flags} open flag{u.open_flags > 1 ? 's' : ''}</Badge>}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">{isError ? 'Could not load this user.' : 'Loading…'}</p>
          )}
          <button onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Close panel">
            <Icon name="chevron" className="h-5 w-5 -rotate-90" />
          </button>
        </header>

        {u && !isPending && (
          <div className="flex-1 space-y-8 overflow-y-auto px-6 py-6">
            {/* ---- actions ---- */}
            {isSelf ? (
              <div className="space-y-3">
              <p className="rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600">
                This is the admin account. Block and delete are disabled here so the admin can never lock themselves out.
              </p>
              <Button onClick={() => setEditing((v) => !v)}>{editing ? 'Cancel edit' : 'Edit details'}</Button>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                <Button disabled={busy} onClick={() => patch({ is_blocked: !u.is_blocked })}>
                  {u.is_blocked ? 'Unblock' : 'Block'}
                </Button>
                {!u.is_verified && (
                  <Button disabled={busy} onClick={() => patch({ is_verified: true })}>Mark verified</Button>
                )}
                <Button disabled={busy} onClick={() => setEditing((v) => !v)}>{editing ? 'Cancel edit' : 'Edit details'}</Button>
                <ConfirmButton
                  disabled={busy}
                  confirmLabel="Delete user and all trips"
                  onConfirm={() => remove.mutate(u.id, { onSuccess: onClose })}
                >
                  Delete
                </ConfirmButton>
              </div>
            )}
            <ErrorNote error={update.error ?? remove.error} fallback="That change did not go through." />

            {editing ? (
              <EditForm
                initial={{
                  name: u.name,
                  email: u.email,
                  password: '',
                  home_town: u.home_town ?? '',
                  phone: u.phone ?? '',
                  date_of_birth: u.date_of_birth ?? '',
                  gender: (u.gender ?? '') as UserUpdate['gender'] | '',
                }}
                busy={busy}
                onSave={(p) => patch(p)}
                onDone={() => setEditing(false)}
                saved={update.isSuccess}
              />
            ) : (
              <Section title="Profile">
                <dl className="grid grid-cols-2 gap-x-6 gap-y-4 text-sm">
                  <Item label="Home town" value={u.home_town} />
                  <Item label="Mobile" value={u.phone} />
                  <Item
                    label="Date of birth"
                    value={u.date_of_birth ? `${formatDay(u.date_of_birth)} (${ageOf(u.date_of_birth)} yrs)` : null}
                  />
                  <Item label="Gender" value={u.gender ? GENDER_LABEL[u.gender] ?? u.gender : null} />
                  <div className="col-span-2">
                    <dt className="text-xs text-slate-500">Travel interests</dt>
                    <dd className="mt-1.5 flex flex-wrap gap-1.5">
                      {u.travel_interests?.length ? (
                        u.travel_interests.map((i) => (
                          <span key={i} className="rounded-full border border-slate-200 px-2.5 py-0.5 text-xs capitalize text-slate-700">
                            {i}
                          </span>
                        ))
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </dd>
                  </div>
                </dl>
              </Section>
            )}

            <Section title="Account">
              <dl className="grid grid-cols-2 gap-x-6 gap-y-4 text-sm">
                <Item label="Joined" value={formatWhen(u.created_at)} />
                <Item label="Last updated" value={formatWhen(u.updated_at)} />
                <Item label="Last login" value={u.last_login_at ? formatWhen(u.last_login_at) : 'Never'} />
                <Item label="Logins" value={String(u.login_count)} />
                <div className="col-span-2">
                  <dt className="text-xs text-slate-500">User ID</dt>
                  <dd className="mt-0.5 font-mono text-xs text-slate-600">{u.id}</dd>
                </div>
              </dl>
            </Section>

            <Section title={`Trips (${u.trips.length})`}>
              <AddTrip userId={u.id} />
              {u.trips.length === 0 ? (
                <p className="text-sm text-slate-400">No trips yet.</p>
              ) : (
                <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200">
                  {u.trips.map((t) => (
                    <TripItem key={t.id} trip={t} />
                  ))}
                </ul>
              )}
            </Section>
          </div>
        )}
      </aside>
    </div>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h3 className="mb-3 text-xs font-semibold tracking-wide text-slate-500 uppercase">{title}</h3>
      {children}
    </section>
  )
}

function Item({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-slate-900">{value || <span className="text-slate-400">—</span>}</dd>
    </div>
  )
}

const TRIP_STATUSES: TripStatus[] = ['processing', 'completed', 'failed']
const PLAN_STATUSES: PlanStatus[] = ['draft', 'saved', 'upcoming', 'completed']

export function TripStatusSelects({ id, status, planStatus }: { id: string; status: string; planStatus: string }) {
  const update = useUpdateTrip()
  const sel =
    'rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 outline-none hover:border-slate-300 focus:border-slate-900 disabled:opacity-50'
  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-1.5">
        <select
          aria-label="Generation status"
          className={sel}
          value={status}
          disabled={update.isPending}
          onChange={(e) => update.mutate({ id, patch: { status: e.target.value as TripStatus } })}
        >
          {TRIP_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select
          aria-label="Plan status"
          className={sel}
          value={planStatus}
          disabled={update.isPending}
          onChange={(e) => update.mutate({ id, patch: { plan_status: e.target.value as PlanStatus } })}
        >
          {PLAN_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <ErrorNote error={update.error} fallback="Could not change the status." />
    </div>
  )
}

function TripItem({ trip }: { trip: AdminTripDetail }) {
  const remove = useDeleteTrip()
  const update = useUpdateTrip()
  const replan = useReplanTrip()
  const [editing, setEditing] = useState(false)
  return (
    <li className="space-y-2 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <Link to={`/trips/${trip.id}`} className="font-medium hover:underline">{trip.destination}</Link>
          <p className="text-xs text-slate-500">
            {formatDay(trip.start_date)} – {formatDay(trip.end_date)} · {trip.travelers} traveller{trip.travelers > 1 ? 's' : ''} · {INR.format(trip.budget)}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap justify-end gap-1">
          <Button onClick={() => setEditing((v) => !v)}>{editing ? 'Close' : 'Edit'}</Button>
          <Button disabled={replan.isPending || trip.status === 'processing'} onClick={() => replan.mutate(trip.id)}>
            Replan
          </Button>
          <ConfirmButton disabled={remove.isPending} confirmLabel="Delete" onConfirm={() => remove.mutate(trip.id)}>
            Delete
          </ConfirmButton>
        </div>
      </div>
      <TripStatusSelects id={trip.id} status={trip.status} planStatus={trip.plan_status} />
      <ErrorNote error={replan.error} fallback="Could not start replanning." />
      {editing && (
        <TripForm
          initial={{
            destination: trip.destination, start_date: trip.start_date, end_date: trip.end_date,
            budget: trip.budget, travelers: trip.travelers, style_tags: trip.style_tags,
          }}
          submitLabel="Save trip"
          note="Saving changes the details only. Use Replan to generate a fresh itinerary."
          busy={update.isPending}
          error={update.error}
          onCancel={() => setEditing(false)}
          onSubmit={(v) => update.mutate({ id: trip.id, patch: v }, { onSuccess: () => setEditing(false) })}
        />
      )}
    </li>
  )
}

function AddTrip({ userId }: { userId: string }) {
  const create = useCreateTripForUser()
  const [open, setOpen] = useState(false)
  if (!open) {
    return (
      <div className="mb-3">
        <Button onClick={() => setOpen(true)}>Add a trip for this user</Button>
      </div>
    )
  }
  return (
    <div className="mb-3">
      <TripForm
        initial={EMPTY_TRIP}
        submitLabel="Create and plan"
        note="The itinerary is generated just as if the user had asked for it, and appears in their dashboard."
        busy={create.isPending}
        error={create.error}
        onCancel={() => setOpen(false)}
        onSubmit={(v) =>
          create.mutate({ userId, payload: { ...v, use_memory: true } }, { onSuccess: () => setOpen(false) })
        }
      />
    </div>
  )
}

function EditForm({
  initial,
  busy,
  onSave,
  onDone,
  saved,
}: {
  initial: {
    name: string
    email: string
    password: string
    home_town: string
    phone: string
    date_of_birth: string
    gender: UserUpdate['gender'] | ''
  }
  busy: boolean
  onSave: (p: UserUpdate) => void
  onDone: () => void
  saved: boolean
}) {
  const [f, setF] = useState(initial)
  const input = 'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-900'
  return (
    <Section title="Edit details">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          const p: UserUpdate = { name: f.name.trim() }
          if (f.email.trim() && f.email.trim() !== initial.email) p.email = f.email.trim()
          if (f.password) p.password = f.password
          if (f.home_town.trim()) p.home_town = f.home_town.trim()
          if (f.phone.trim()) p.phone = f.phone.trim()
          if (f.date_of_birth) p.date_of_birth = f.date_of_birth
          if (f.gender) p.gender = f.gender
          onSave(p)
        }}
        className="grid grid-cols-2 gap-3 text-sm"
      >
        <label className="col-span-2 space-y-1">
          <span className="text-xs text-slate-500">Name</span>
          <input className={input} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required />
        </label>
        <label className="col-span-2 space-y-1">
          <span className="text-xs text-slate-500">Email</span>
          <input type="email" className={input} value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} required />
        </label>
        <label className="col-span-2 space-y-1">
          <span className="text-xs text-slate-500">Set a new password (leave blank to keep the current one)</span>
          <input
            type="password"
            className={input}
            value={f.password}
            autoComplete="new-password"
            pattern="(?=.*[A-Za-z])(?=.*\d).{8,}"
            title="At least 8 characters, with letters and numbers"
            onChange={(e) => setF({ ...f, password: e.target.value })}
          />
        </label>
        <label className="space-y-1">
          <span className="text-xs text-slate-500">Home town</span>
          <input className={input} value={f.home_town} onChange={(e) => setF({ ...f, home_town: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-xs text-slate-500">Mobile</span>
          <input className={input} value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-xs text-slate-500">Date of birth</span>
          <input type="date" className={input} value={f.date_of_birth} onChange={(e) => setF({ ...f, date_of_birth: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-xs text-slate-500">Gender</span>
          <select className={input} value={f.gender ?? ''} onChange={(e) => setF({ ...f, gender: e.target.value as UserUpdate['gender'] })}>
            <option value="">—</option>
            {Object.entries(GENDER_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        <div className="col-span-2 flex items-center gap-2 pt-1">
          <Button type="submit" variant="primary" disabled={busy}>{busy ? 'Saving…' : 'Save'}</Button>
          <Button onClick={onDone}>Close</Button>
          {saved && <span className="text-xs text-emerald-700">Saved</span>}
        </div>
      </form>
    </Section>
  )
}
