import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiErrorMessage, useAuth } from '@/lib/auth'
import { Icon, type IconName } from '@/components/Icon'
import { PackageEditor } from '@/features/packages/PackageEditor'
import { CityField } from '@/components/CityField'
import { coverTone, mediaUrl } from '@/lib/media'
import type { TravelPackage } from '@/features/admin/types'
import {
  useBizBookings, useBizPackages, useDeleteBizPackage, useMyBusiness, useSaveBizPackage, useSetBizBooking,
  useUpdateBusiness, type Business,
} from './api'

const INR = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })
const fmt = (iso: string) => new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })

type Tab = 'overview' | 'packages' | 'bookings' | 'profile'
const TABS: { key: Tab; label: string; icon: IconName }[] = [
  { key: 'overview', label: 'Overview', icon: 'dashboard' },
  { key: 'packages', label: 'Packages', icon: 'bag' },
  { key: 'bookings', label: 'Bookings', icon: 'calendar' },
  { key: 'profile', label: 'Business profile', icon: 'landmark' },
]

export function BusinessDashboardPage() {
  const { data: biz, isPending, isError } = useMyBusiness()
  const [tab, setTab] = useState<Tab>('overview')

  if (isPending) return <div className="h-64 animate-pulse rounded-3xl bg-slate-200/60" />
  if (isError || !biz) return <p className="text-sm text-red-700">Could not load your business.</p>

  return (
    <div className="space-y-8">
      <Hero biz={biz} />
      <StatusBanner biz={biz} />

      <div className="inline-flex max-w-full overflow-x-auto rounded-xl border border-slate-200 bg-white p-1 text-sm">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-4 py-2 transition ${
              tab === t.key ? 'bg-ink font-medium text-white' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Icon name={t.icon} className={`h-4 w-4 ${tab === t.key ? 'text-gold' : 'text-slate-400'}`} />
            {t.label}
            {t.key === 'bookings' && biz.bookings_pending > 0 && (
              <span className="rounded-full bg-gold px-1.5 text-[11px] font-semibold text-ink">{biz.bookings_pending}</span>
            )}
          </button>
        ))}
      </div>

      {tab === 'overview' && <Overview biz={biz} go={setTab} />}
      {tab === 'packages' && <Packages biz={biz} />}
      {tab === 'bookings' && <Bookings approved={biz.status === 'approved'} />}
      {tab === 'profile' && <Profile biz={biz} />}
    </div>
  )
}

function Hero({ biz }: { biz: Business }) {
  const { user } = useAuth()
  return (
    <section className="relative overflow-hidden rounded-3xl bg-ink px-6 py-8 text-white sm:px-10 sm:py-10">
      <div aria-hidden className="pointer-events-none absolute -top-32 -right-24 h-96 w-96 rounded-full bg-gold/25 blur-[110px]" />
      <div aria-hidden className="pointer-events-none absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-gold/60 to-transparent" />
      <div className="relative flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="flex items-center gap-2 text-xs font-semibold tracking-[0.2em] text-gold uppercase">
            <Icon name="landmark" className="h-4 w-4" /> Partner dashboard
          </p>
          <h1 className="font-display mt-3 text-4xl leading-tight tracking-tight sm:text-5xl">{biz.business_name}</h1>
          <p className="mt-2 text-slate-400">
            {biz.city} · run by {user?.name}
          </p>
        </div>
        {biz.status === 'approved' && <ShareLink slug={biz.slug} />}
      </div>
    </section>
  )
}

function ShareLink({ slug }: { slug: string }) {
  const [copied, setCopied] = useState(false)
  const url = `${window.location.origin}/b/${slug}`
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Link to={`/b/${slug}`} className="rounded-xl border border-white/15 px-4 py-2.5 text-sm text-slate-200 hover:border-gold/60">
        View public page
      </Link>
      <button
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(url)
            setCopied(true)
            setTimeout(() => setCopied(false), 1800)
          } catch {
            /* clipboard blocked */
          }
        }}
        className="rounded-xl bg-gradient-to-b from-gold-light to-gold px-4 py-2.5 text-sm font-semibold text-ink"
      >
        {copied ? 'Link copied' : 'Copy share link'}
      </button>
    </div>
  )
}

function StatusBanner({ biz }: { biz: Business }) {
  if (biz.status === 'approved') return null
  const map = {
    pending: {
      cls: 'border-gold/40 bg-gold/10 text-gold-dark',
      title: 'Your business is waiting for approval',
      body: 'Our team reviews every partner before their packages go live. You can already set up your profile; publishing unlocks once approved.',
    },
    rejected: {
      cls: 'border-red-200 bg-red-50 text-red-800',
      title: 'Your application was not approved',
      body: biz.status_reason ?? 'Update your business details and contact support to be reviewed again.',
    },
    suspended: {
      cls: 'border-red-200 bg-red-50 text-red-800',
      title: 'Your business is suspended',
      body: biz.status_reason ?? 'Your packages are hidden from travellers. Contact support for details.',
    },
  } as const
  const m = map[biz.status]
  return (
    <div className={`rounded-2xl border px-5 py-4 ${m.cls}`}>
      <p className="font-semibold">{m.title}</p>
      <p className="mt-1 text-sm opacity-90">{m.body}</p>
    </div>
  )
}

function Overview({ biz, go }: { biz: Business; go: (t: Tab) => void }) {
  const { data: pkgs } = useBizPackages()
  const { data: bookings } = useBizBookings('')
  const confirmed = (bookings?.items ?? []).filter((b) => b.status === 'confirmed')
  const revenue = confirmed.reduce((s, b) => s + b.total_price, 0)
  const travellers = confirmed.reduce((s, b) => s + b.travelers, 0)
  const live = (pkgs ?? []).filter((p) => p.is_active).length

  return (
    <div className="space-y-6">
      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-slate-200 bg-slate-200 lg:grid-cols-4">
        {[
          { label: 'Live packages', value: String(live) },
          { label: 'Bookings to confirm', value: String(biz.bookings_pending) },
          { label: 'Confirmed travellers', value: String(travellers) },
          { label: 'Confirmed booking value', value: INR.format(revenue) },
        ].map((s) => (
          <div key={s.label} className="bg-white px-6 py-5">
            <dt className="text-sm text-slate-500">{s.label}</dt>
            <dd className="font-display mt-2 text-4xl tracking-tight tabular-nums">{s.value}</dd>
          </div>
        ))}
      </dl>

      <div className="grid gap-4 md:grid-cols-3">
        {[
          { icon: 'plus' as IconName, title: 'Publish a package', body: 'Create a ready-made trip travellers can opt into.', tab: 'packages' as Tab },
          { icon: 'calendar' as IconName, title: 'Review bookings', body: 'Confirm or decline requests for your packages.', tab: 'bookings' as Tab },
          { icon: 'landmark' as IconName, title: 'Polish your profile', body: 'Your public page is what travellers see first.', tab: 'profile' as Tab },
        ].map((c) => (
          <button
            key={c.title}
            onClick={() => go(c.tab)}
            className="group rounded-2xl border border-slate-200 bg-white p-6 text-left shadow-sm transition hover:border-slate-300"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-ink text-gold">
              <Icon name={c.icon} className="h-5 w-5" />
            </span>
            <span className="mt-4 flex items-center gap-1.5 font-semibold">
              {c.title} <Icon name="arrow" className="h-3.5 w-3.5 text-slate-400 transition group-hover:translate-x-0.5" />
            </span>
            <span className="mt-1 block text-sm text-slate-500">{c.body}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function Packages({ biz }: { biz: Business }) {
  const { data, isPending } = useBizPackages()
  const save = useSaveBizPackage()
  const remove = useDeleteBizPackage()
  const [editing, setEditing] = useState<TravelPackage | 'new' | null>(null)
  const approved = biz.status === 'approved'

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-500">
          {approved ? 'Packages appear on the public Packages page and your business page.' : 'Publishing unlocks once your business is approved.'}
        </p>
        <button
          disabled={!approved}
          onClick={() => setEditing(editing === 'new' ? null : 'new')}
          className="inline-flex items-center gap-2 rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
        >
          <Icon name="plus" className="h-4 w-4 text-gold" /> {editing === 'new' ? 'Close' : 'New package'}
        </button>
      </div>

      {editing && (
        <PackageEditor
          fillPath="/business/packages/fill"
          key={editing === 'new' ? 'new' : editing.id}
          pkg={editing === 'new' ? null : editing}
          busy={save.isPending}
          error={save.error}
          onCancel={() => setEditing(null)}
          onSubmit={(payload) =>
            save.mutate({ id: editing === 'new' ? undefined : editing.id, payload }, { onSuccess: () => setEditing(null) })
          }
        />
      )}

      {isPending && <p className="text-sm text-slate-500">Loading…</p>}
      {data?.length === 0 && !editing && (
        <p className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
          No packages yet.
        </p>
      )}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data?.map((p) => (
          <article key={p.id} className={`flex flex-col overflow-hidden rounded-2xl border bg-white shadow-sm ${p.is_active ? 'border-slate-200' : 'border-dashed border-slate-300 opacity-75'}`}>
            <div className={`h-32 bg-gradient-to-br ${coverTone(p.title)}`}>
              {p.images?.[0] && <img src={mediaUrl(p.images[0])} alt="" className="h-full w-full object-cover" loading="lazy" />}
            </div>
            <div className="flex flex-1 flex-col p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="truncate font-semibold">{p.title}</h3>
                <p className="text-sm text-slate-500">{p.destination} · {p.duration_days} days</p>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${p.is_active ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : 'bg-slate-100 text-slate-500 ring-slate-200'}`}>
                {p.is_active ? 'Live' : 'Hidden'}
              </span>
            </div>
            <p className="mt-4 text-xl font-semibold">{INR.format(p.price_per_person)} <span className="text-sm font-normal text-slate-500">/ person</span></p>
            <p className="mt-1 text-xs text-slate-500">
              {p.booking_count} booking{p.booking_count === 1 ? '' : 's'}
              {p.seats != null ? ` · ${p.seats_left} seats left` : ''}
            </p>
            <div className="mt-5 flex flex-wrap gap-2 border-t border-slate-100 pt-4 text-sm">
              <button disabled={!approved} onClick={() => setEditing(p)} className="rounded-lg border border-slate-200 px-3 py-1.5 hover:bg-slate-50 disabled:opacity-40">Edit</button>
              {approved && p.is_active && (
                <Link to={`/packages/${p.id}`} className="rounded-lg border border-slate-200 px-3 py-1.5 hover:bg-slate-50">View</Link>
              )}
              <DeleteButton onConfirm={() => remove.mutate(p.id)} busy={remove.isPending} />
            </div>
            </div>
          </article>
        ))}
      </div>
      {remove.error != null && <p className="text-sm text-red-700">{apiErrorMessage(remove.error, 'Could not delete.')}</p>}
    </div>
  )
}

function DeleteButton({ onConfirm, busy }: { onConfirm: () => void; busy: boolean }) {
  const [armed, setArmed] = useState(false)
  return armed ? (
    <span className="ml-auto flex gap-2">
      <button disabled={busy} onClick={onConfirm} className="rounded-lg bg-red-600 px-3 py-1.5 text-white">Delete</button>
      <button onClick={() => setArmed(false)} className="rounded-lg border border-slate-200 px-3 py-1.5">Keep</button>
    </span>
  ) : (
    <button onClick={() => setArmed(true)} className="ml-auto rounded-lg px-3 py-1.5 text-slate-500 hover:text-red-600">Delete</button>
  )
}

const PILL: Record<string, string> = {
  pending: 'bg-gold/10 text-gold-dark ring-gold/40',
  confirmed: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  cancelled: 'bg-slate-100 text-slate-500 ring-slate-200',
}

function Bookings({ approved }: { approved: boolean }) {
  const [status, setStatus] = useState('pending')
  const { data, isPending } = useBizBookings(status)
  const set = useSetBizBooking()

  return (
    <div className="space-y-4">
      <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 text-sm">
        {[['pending', 'To confirm'], ['confirmed', 'Confirmed'], ['cancelled', 'Cancelled'], ['', 'All']].map(([v, l]) => (
          <button key={v} onClick={() => setStatus(v)} className={`rounded-md px-3 py-1.5 ${status === v ? 'bg-ink text-white' : 'text-slate-600'}`}>
            {l}
          </button>
        ))}
      </div>
      {isPending && <p className="text-sm text-slate-500">Loading…</p>}
      {data?.items.length === 0 && (
        <p className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">No bookings here.</p>
      )}
      <ul className="space-y-3">
        {data?.items.map((b) => (
          <li key={b.id} className="flex flex-wrap items-center gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ink text-xs font-semibold text-gold-light">
              {(b.user_name ?? '?').split(/\s+/).map((p) => p[0]).join('').slice(0, 2).toUpperCase()}
            </span>
            <div className="min-w-0 flex-1">
              <p className="font-semibold">{b.package_title}</p>
              <p className="text-sm text-slate-500">
                {b.user_name} · {b.user_email} · {b.travelers} traveller{b.travelers > 1 ? 's' : ''}
              </p>
              <p className="text-xs text-slate-400">
                {fmt(b.start_date)} – {fmt(b.end_date)} · {INR.format(b.total_price)}
                {b.note ? ` · “${b.note}”` : ''}
              </p>
            </div>
            <span className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ring-1 ${PILL[b.status]}`}>{b.status}</span>
            {approved && (
              <div className="flex gap-2 text-sm">
                {b.status !== 'confirmed' && (
                  <button disabled={set.isPending} onClick={() => set.mutate({ id: b.id, status: 'confirmed' })} className="rounded-lg bg-ink px-3 py-1.5 font-medium text-white">
                    Confirm
                  </button>
                )}
                {b.status !== 'cancelled' && (
                  <button disabled={set.isPending} onClick={() => set.mutate({ id: b.id, status: 'cancelled' })} className="rounded-lg border border-slate-200 px-3 py-1.5">
                    Decline
                  </button>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

function Profile({ biz }: { biz: Business }) {
  const save = useUpdateBusiness()
  const [f, setF] = useState({
    business_name: biz.business_name, kind: biz.kind, city: biz.city,
    business_phone: biz.business_phone, description: biz.description,
    website: biz.website ?? '', gst_number: biz.gst_number ?? '',
  })
  const [saved, setSaved] = useState(false)
  const input = 'w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-slate-900'
  const cap = 'text-xs font-medium text-slate-600'

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        setSaved(false)
        save.mutate(
          { ...f, website: f.website.trim() || null, gst_number: f.gst_number.trim() || null },
          { onSuccess: () => setSaved(true) },
        )
      }}
      className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="space-y-1"><span className={cap}>Business name</span>
          <input className={input} required value={f.business_name} onChange={(e) => setF({ ...f, business_name: e.target.value })} /></label>
        <label className="space-y-1"><span className={cap}>Type</span>
          <select className={input} value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>
            <option value="agency">Travel agency</option>
            <option value="tour_operator">Tour operator</option>
            <option value="hotel">Hotel / stay</option>
            <option value="other">Other</option>
          </select></label>
        <div className="sm:col-span-2">
          <CityField label="City" value={f.city} onChange={(v) => setF({ ...f, city: v })} />
        </div>
        <label className="space-y-1"><span className={cap}>Business phone</span>
          <input className={input} required value={f.business_phone} onChange={(e) => setF({ ...f, business_phone: e.target.value })} /></label>
        <label className="space-y-1"><span className={cap}>Website</span>
          <input className={input} value={f.website} onChange={(e) => setF({ ...f, website: e.target.value })} /></label>
        <label className="space-y-1"><span className={cap}>GSTIN</span>
          <input className={input} value={f.gst_number} onChange={(e) => setF({ ...f, gst_number: e.target.value.toUpperCase() })} /></label>
        <label className="space-y-1 sm:col-span-2"><span className={cap}>About your business</span>
          <textarea rows={4} className={input} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></label>
      </div>
      <p className="text-xs text-slate-500">Public page: {window.location.origin}/b/{biz.slug} — changes if you rename the business.</p>
      {save.error != null && <p className="rounded-xl bg-red-50 px-4 py-2.5 text-sm text-red-700">{apiErrorMessage(save.error, 'Could not save.')}</p>}
      <div className="flex items-center justify-end gap-4">
        {saved && <span className="flex items-center gap-1.5 text-sm text-emerald-700"><Icon name="check" className="h-4 w-4" /> Saved</span>}
        <button type="submit" disabled={save.isPending} className="rounded-xl bg-ink px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
          {save.isPending ? 'Saving…' : 'Save profile'}
        </button>
      </div>
    </form>
  )
}
