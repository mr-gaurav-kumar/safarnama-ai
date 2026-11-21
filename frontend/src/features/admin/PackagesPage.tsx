import { useState } from 'react'
import { useAdminPackages, useDeletePackage, useSavePackage } from './api'
import { Badge, Button, ConfirmButton, ErrorNote, PageHeader } from './ui'
import type { TravelPackage } from './types'
import { PackageEditor } from '@/features/packages/PackageEditor'
import { coverTone, mediaUrl } from '@/lib/media'

const INR = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

export function PackagesPage() {
  const { data, isPending, isError } = useAdminPackages()
  const [editing, setEditing] = useState<TravelPackage | 'new' | null>(null)
  const save = useSavePackage()

  return (
    <>
      <PageHeader title="Packages" subtitle="Ready-made trips every traveller can see and opt into.">
        <Button variant="primary" onClick={() => setEditing(editing === 'new' ? null : 'new')}>
          {editing === 'new' ? 'Close' : 'New package'}
        </Button>
      </PageHeader>

      {editing && (
        <PackageEditor
          fillPath="/admin/packages/fill"
          key={editing === 'new' ? 'new' : editing.id}
          pkg={editing === 'new' ? null : editing}
          busy={save.isPending}
          error={save.error}
          onCancel={() => setEditing(null)}
          onSubmit={(payload) =>
            save.mutate(
              { id: editing === 'new' ? undefined : editing.id, payload },
              { onSuccess: () => setEditing(null) },
            )
          }
        />
      )}

      {isPending && <p className="text-sm text-slate-500">Loading…</p>}
      {isError && <p className="text-sm text-red-700">Could not load packages.</p>}
      {data && data.length === 0 && !editing && (
        <p className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
          No packages yet. Create the first one — it appears on every traveller’s Packages page.
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data?.map((p) => (
          <PackageCard key={p.id} pkg={p} onEdit={() => setEditing(p)} />
        ))}
      </div>
    </>
  )
}

function PackageCard({ pkg, onEdit }: { pkg: TravelPackage; onEdit: () => void }) {
  const save = useSavePackage()
  const remove = useDeletePackage()
  const { id, seats_left, created_at, booking_count, business_name, business_slug, ...input } = pkg
  void seats_left; void created_at; void booking_count; void business_name; void business_slug
  return (
    <article className={`flex flex-col overflow-hidden rounded-2xl border bg-white shadow-sm ${pkg.is_active ? 'border-slate-200' : 'border-dashed border-slate-300 opacity-75'}`}>
      <div className={`relative h-36 bg-gradient-to-br ${coverTone(pkg.title)}`}>
        {pkg.images?.[0] && <img src={mediaUrl(pkg.images[0])} alt="" className="h-full w-full object-cover" loading="lazy" />}
        <span className="absolute right-3 bottom-3 rounded-full bg-black/60 px-2 py-0.5 text-[11px] text-white">
          {pkg.images?.length ? `${pkg.images.length} photo${pkg.images.length > 1 ? 's' : ''}` : 'No photos yet'}
        </span>
      </div>
      <div className="flex flex-1 flex-col p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold">{pkg.title}</h3>
          <p className="text-sm text-slate-500">{pkg.destination}</p>
          <p className="mt-0.5 text-xs text-slate-400">by {pkg.business_name ?? 'Safarnama'}</p>
        </div>
        <Badge tone={pkg.is_active ? 'good' : 'neutral'}>{pkg.is_active ? 'live' : 'hidden'}</Badge>
      </div>
      {pkg.summary && <p className="mt-3 line-clamp-2 text-sm text-slate-600">{pkg.summary}</p>}
      <dl className="mt-4 grid grid-cols-3 gap-2 text-sm">
        <div>
          <dt className="text-xs text-slate-500">Price / person</dt>
          <dd className="font-semibold">{INR.format(pkg.price_per_person)}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Duration</dt>
          <dd className="font-semibold">{pkg.duration_days} days</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Bookings</dt>
          <dd className="font-semibold">
            {pkg.booking_count}
            {pkg.seats != null && <span className="font-normal text-slate-500"> · {pkg.seats_left} left</span>}
          </dd>
        </div>
      </dl>
      <div className="mt-5 flex flex-wrap gap-1 border-t border-slate-100 pt-4">
        <Button onClick={onEdit}>Edit</Button>
        <Button
          disabled={save.isPending}
          onClick={() => save.mutate({ id, payload: { ...input, is_active: !pkg.is_active } })}
        >
          {pkg.is_active ? 'Hide' : 'Publish'}
        </Button>
        <ConfirmButton disabled={remove.isPending} confirmLabel="Delete with bookings" onConfirm={() => remove.mutate(id)}>
          Delete
        </ConfirmButton>
      </div>
      <ErrorNote error={save.error ?? remove.error} fallback="That change did not go through." />
      </div>
    </article>
  )
}

