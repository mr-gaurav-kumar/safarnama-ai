import { useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  formatWhen, useBlockBusiness, useBusinesses, useCreateBusiness, useSetBusinessStatus, useUpdateBusiness,
} from './api'
import { Button, ErrorNote, Filter, PageHeader, Pagination, SearchBox, useDebounced, usePaged } from './ui'
import type { Business, BusinessFields, BusinessKind } from './types'

const STATUSES = [
  { value: 'pending', label: 'Waiting for approval' },
  { value: 'approved', label: 'Approved' },
  { value: 'suspended', label: 'Suspended' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'blocked', label: 'Blocked' },
  { value: '', label: 'All' },
]

const KIND: Record<BusinessKind, string> = {
  agency: 'Travel agency', tour_operator: 'Tour operator', hotel: 'Hotel / stay', other: 'Other business',
}

const PILL: Record<string, string> = {
  pending: 'bg-gold/10 text-gold-dark ring-gold/40',
  approved: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  suspended: 'bg-red-50 text-red-700 ring-red-200',
  rejected: 'bg-slate-100 text-slate-500 ring-slate-200',
}

const field = 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-900'

/**
 * Merchants (business accounts). The admin can add one directly, edit its
 * profile, approve / reject / suspend it, and block it. Travellers only ever
 * see a merchant that is approved AND not blocked -- the backend enforces
 * that on every package list, package page, public page and booking.
 */
export function BusinessesPage() {
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [creating, setCreating] = useState(false)
  const q = useDebounced(search)
  const paged = usePaged(20)
  const { data, isPending, isError } = useBusinesses(status, q, paged.limit, paged.offset)

  return (
    <>
      <PageHeader
        title="Merchants"
        subtitle="Agencies and businesses that publish packages. Travellers only see a merchant that is approved and not blocked."
      >
        <Button variant="primary" onClick={() => setCreating((v) => !v)}>
          {creating ? 'Close' : 'Add merchant'}
        </Button>
      </PageHeader>

      {creating && <CreateMerchantForm onDone={() => setCreating(false)} />}

      <div className="flex flex-wrap items-center gap-3">
        <SearchBox value={search} onChange={(v) => { setSearch(v); paged.reset() }} placeholder="Name, city or email" />
        <Filter label="Status" value={status} onChange={(v) => { setStatus(v); paged.reset() }} options={STATUSES} />
      </div>

      {isPending && <p className="text-sm text-slate-500">Loading…</p>}
      {isError && <p className="text-sm text-red-700">Could not load merchants.</p>}
      {data?.items.length === 0 && (
        <p className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
          {status === 'pending' ? 'No applications waiting. All caught up.' : 'No merchants here.'}
        </p>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        {data?.items.map((b) => <MerchantCard key={b.user_id} b={b} />)}
      </div>
      {data && data.total > paged.limit && <Pagination total={data.total} paged={paged} />}
    </>
  )
}

// ---------------------------------------------------------------- card

function MerchantCard({ b }: { b: Business }) {
  const set = useSetBusinessStatus()
  const block = useBlockBusiness()
  const [reason, setReason] = useState('')
  const [asking, setAsking] = useState<null | 'rejected' | 'suspended' | 'blocked'>(null)
  const [editing, setEditing] = useState(false)
  const busy = set.isPending || block.isPending
  const initials = b.business_name.split(/\s+/).map((p) => p[0]).join('').slice(0, 2).toUpperCase()

  function confirmAsk() {
    const why = reason.trim() || undefined
    const done = { onSuccess: () => { setAsking(null); setReason('') } }
    if (asking === 'blocked') block.mutate({ id: b.user_id, blocked: true, reason: why }, done)
    else if (asking) set.mutate({ id: b.user_id, status: asking, reason: why }, done)
  }

  return (
    <article className={`flex flex-col rounded-2xl border bg-white p-5 shadow-sm sm:p-6 ${b.owner_blocked ? 'border-red-300' : 'border-slate-200'}`}>
      <div className="flex items-start gap-4">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-ink text-sm font-semibold text-gold-light ring-2 ring-gold/20">
          {initials}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-lg font-semibold">{b.business_name}</h3>
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ring-1 ${PILL[b.status]}`}>{b.status}</span>
            {b.owner_blocked && (
              <span className="rounded-full bg-red-600 px-2.5 py-0.5 text-xs font-semibold text-white">Blocked</span>
            )}
          </div>
          <p className="text-sm text-slate-500">{KIND[b.kind as BusinessKind] ?? b.kind} · {b.city}</p>
          <p className={`mt-1 text-xs font-medium ${b.is_visible ? 'text-emerald-700' : 'text-slate-500'}`}>
            {b.is_visible ? '● Visible to travellers' : '○ Hidden from travellers'}
          </p>
        </div>
      </div>

      {editing ? (
        <EditMerchantForm b={b} onDone={() => setEditing(false)} />
      ) : (
        <>
          {b.description && <p className="mt-4 line-clamp-3 text-sm text-slate-600">{b.description}</p>}
          <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <Item label="Owner" value={b.owner_name ?? '—'} sub={b.owner_email ?? undefined} />
            <Item label="Business phone" value={b.business_phone} />
            <Item label="GSTIN" value={b.gst_number ?? 'Not given'} />
            <Item
              label="Website"
              value={b.website ? <a href={b.website} target="_blank" rel="noreferrer" className="text-gold-dark underline">{b.website.replace(/^https?:\/\//, '')}</a> : 'Not given'}
            />
            <Item label="Joined" value={formatWhen(b.created_at)} />
            <Item label="Packages · pending bookings" value={`${b.package_count} · ${b.bookings_pending}`} />
          </dl>
        </>
      )}

      {b.status_reason && !editing && (
        <p className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">Note: {b.status_reason}</p>
      )}

      {!editing && (
        <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
          {b.owner_blocked ? (
            <button
              disabled={busy}
              onClick={() => block.mutate({ id: b.user_id, blocked: false })}
              className="rounded-lg bg-gradient-to-b from-gold-light to-gold px-4 py-1.5 text-sm font-semibold text-ink shadow-sm disabled:opacity-50"
            >
              Unblock
            </button>
          ) : (
            <>
              {b.status !== 'approved' && (
                <button
                  disabled={busy}
                  onClick={() => set.mutate({ id: b.user_id, status: 'approved' })}
                  className="rounded-lg bg-gradient-to-b from-gold-light to-gold px-4 py-1.5 text-sm font-semibold text-ink shadow-sm disabled:opacity-50"
                >
                  {b.status === 'suspended' ? 'Reinstate' : 'Approve'}
                </button>
              )}
              {b.status === 'pending' && <Button disabled={busy} onClick={() => setAsking('rejected')}>Reject</Button>}
              {b.status === 'approved' && <Button disabled={busy} onClick={() => setAsking('suspended')}>Suspend</Button>}
            </>
          )}
          <Button disabled={busy} onClick={() => setEditing(true)}>Edit</Button>
          {!b.owner_blocked && <Button variant="danger" disabled={busy} onClick={() => setAsking('blocked')}>Block</Button>}
          {b.is_visible && (
            <Link to={`/b/${b.slug}`} className="ml-auto text-sm font-medium text-slate-600 hover:text-slate-950">
              Public page →
            </Link>
          )}
        </div>
      )}

      {asking && (
        <div className="mt-3 space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
          {asking === 'blocked' && (
            <p className="text-xs text-slate-600">
              Blocking signs the owner out everywhere and stops them logging in. Their packages and public page
              disappear for travellers, and nobody can book them. You can unblock any time.
            </p>
          )}
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={300}
            placeholder={
              asking === 'rejected' ? 'Reason (shown to the business)' : asking === 'blocked' ? 'Reason for blocking' : 'Reason for suspending'
            }
            className={field}
          />
          <div className="flex gap-2">
            <Button variant="danger" disabled={busy} onClick={confirmAsk}>
              {{ rejected: 'Reject application', suspended: 'Suspend merchant', blocked: 'Block merchant' }[asking]}
            </Button>
            <Button onClick={() => setAsking(null)}>Cancel</Button>
          </div>
        </div>
      )}
      <ErrorNote error={set.error ?? block.error} fallback="That change did not go through." />
    </article>
  )
}

// ---------------------------------------------------------------- forms

const emptyFields: BusinessFields = {
  business_name: '', kind: 'agency', city: '', business_phone: '', description: '', website: null, gst_number: null,
}

/** The profile inputs shared by "add" and "edit". */
function ProfileInputs({ v, set }: { v: BusinessFields; set: (v: BusinessFields) => void }) {
  const on = (k: keyof BusinessFields) => (e: { target: { value: string } }) => set({ ...v, [k]: e.target.value })
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Labeled label="Business name">
        <input className={field} value={v.business_name} onChange={on('business_name')} required minLength={2} maxLength={160} />
      </Labeled>
      <Labeled label="Type">
        <select className={field} value={v.kind} onChange={on('kind')}>
          {(Object.keys(KIND) as BusinessKind[]).map((k) => <option key={k} value={k}>{KIND[k]}</option>)}
        </select>
      </Labeled>
      <Labeled label="City">
        <input className={field} value={v.city} onChange={on('city')} required minLength={2} maxLength={120} />
      </Labeled>
      <Labeled label="Business phone">
        <input className={field} value={v.business_phone} onChange={on('business_phone')} required placeholder="+91 98765 43210" />
      </Labeled>
      <Labeled label="Website (optional)">
        <input className={field} value={v.website ?? ''} onChange={on('website')} maxLength={200} placeholder="example.in" />
      </Labeled>
      <Labeled label="GSTIN (optional)">
        <input className={field} value={v.gst_number ?? ''} onChange={on('gst_number')} maxLength={15} placeholder="15 characters" />
      </Labeled>
      <Labeled label="About" wide>
        <textarea className={field} rows={3} value={v.description} onChange={on('description')} maxLength={2000} />
      </Labeled>
    </div>
  )
}

/** Blank optional strings go to the API as null. */
const clean = (v: BusinessFields): BusinessFields => ({
  ...v,
  website: v.website?.trim() || null,
  gst_number: v.gst_number?.trim() || null,
})

function EditMerchantForm({ b, onDone }: { b: Business; onDone: () => void }) {
  const update = useUpdateBusiness()
  const [v, setV] = useState<BusinessFields>({
    business_name: b.business_name, kind: b.kind as BusinessKind, city: b.city, business_phone: b.business_phone,
    description: b.description, website: b.website, gst_number: b.gst_number,
  })
  function submit(e: FormEvent) {
    e.preventDefault()
    update.mutate({ id: b.user_id, body: clean(v) }, { onSuccess: onDone })
  }
  return (
    <form onSubmit={submit} className="mt-4 space-y-3">
      <ProfileInputs v={v} set={setV} />
      <p className="text-xs text-slate-500">
        To change the owner’s name, email or password, use the Users page. Renaming the business moves its public page to a new link.
      </p>
      <ErrorNote error={update.error} fallback="Could not save the merchant." />
      <div className="flex gap-2">
        <Button type="submit" variant="primary" disabled={update.isPending}>{update.isPending ? 'Saving…' : 'Save changes'}</Button>
        <Button onClick={onDone}>Cancel</Button>
      </div>
    </form>
  )
}

function CreateMerchantForm({ onDone }: { onDone: () => void }) {
  const create = useCreateBusiness()
  const [v, setV] = useState<BusinessFields>(emptyFields)
  const [ownerName, setOwnerName] = useState('')
  const [ownerEmail, setOwnerEmail] = useState('')
  const [password, setPassword] = useState('')
  const [live, setLive] = useState(true)

  function submit(e: FormEvent) {
    e.preventDefault()
    create.mutate(
      {
        ...clean(v), owner_name: ownerName, owner_email: ownerEmail, password,
        is_verified: true, status: live ? 'approved' : 'pending',
      },
      { onSuccess: onDone },
    )
  }

  return (
    <form onSubmit={submit} className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
      <p className="text-sm text-slate-600">
        Creates the merchant’s login and business profile together. No email is sent — share the login with the merchant yourself.
      </p>
      <h3 className="text-sm font-semibold text-slate-900">Owner’s login</h3>
      <div className="grid gap-3 sm:grid-cols-3">
        <Labeled label="Owner name">
          <input className={field} value={ownerName} onChange={(e) => setOwnerName(e.target.value)} required maxLength={120} />
        </Labeled>
        <Labeled label="Email">
          <input className={field} type="email" value={ownerEmail} onChange={(e) => setOwnerEmail(e.target.value)} required />
        </Labeled>
        <Labeled label="Password">
          <input
            className={field} type="password" value={password} minLength={8} maxLength={72}
            pattern="(?=.*[A-Za-z])(?=.*\d).{8,}" title="At least 8 characters, with letters and numbers"
            onChange={(e) => setPassword(e.target.value)} required
          />
        </Labeled>
      </div>
      <h3 className="text-sm font-semibold text-slate-900">Business</h3>
      <ProfileInputs v={v} set={setV} />
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} />
        Approve now (their packages go live as soon as they publish)
      </label>
      <ErrorNote error={create.error} fallback="Could not create that merchant." />
      <div className="flex gap-2">
        <Button type="submit" variant="primary" disabled={create.isPending}>{create.isPending ? 'Creating…' : 'Create merchant'}</Button>
        <Button onClick={onDone}>Cancel</Button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------- bits

function Labeled({ label, children, wide }: { label: string; children: ReactNode; wide?: boolean }) {
  return (
    <label className={`space-y-1 text-sm ${wide ? 'sm:col-span-2' : ''}`}>
      <span className="text-slate-600">{label}</span>
      {children}
    </label>
  )
}

function Item({ label, value, sub }: { label: string; value: ReactNode; sub?: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="truncate text-slate-900">{value}</dd>
      {sub && <dd className="truncate text-xs text-slate-500">{sub}</dd>}
    </div>
  )
}
