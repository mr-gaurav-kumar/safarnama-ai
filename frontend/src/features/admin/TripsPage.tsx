import { useState } from 'react'
import { formatDay, formatWhen, useAdminTrips, useDeleteTrip, useReplanTrip, useUpdateTrip } from './api'
import {
  Button, ConfirmButton, ErrorNote, Filter, PageHeader, Pagination, SearchBox,
  StatusBadge, TableCard, Td, Th, useDebounced, usePaged,
} from './ui'
import type { AdminTrip } from './types'
import { TripStatusSelects } from './UserDrawer'
import { TripForm } from './TripForm'
import { Fragment } from 'react'

const STATUSES = [
  { value: '', label: 'All' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
]

export function TripsPage() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const q = useDebounced(search)
  const paged = usePaged(25)

  const { data, isPending, isError } = useAdminTrips(q, status, paged.limit, paged.offset)

  return (
    <>
      <PageHeader title="Trips" subtitle="Every trip in the system, newest first. Change a status from the dropdowns." />

      <div className="flex flex-wrap items-center gap-3">
        <SearchBox
          value={search}
          onChange={(v) => { setSearch(v); paged.reset() }}
          placeholder="Destination or owner email"
        />
        <Filter
          label="Status"
          value={status}
          onChange={(v) => { setStatus(v); paged.reset() }}
          options={STATUSES}
        />
      </div>

      <TableCard
        colSpan={5}
        isPending={isPending}
        isError={isError}
        isEmpty={data?.items.length === 0}
        emptyText="No trip matches that."
        head={
          <tr>
            <Th>Trip</Th>
            <Th>Owner</Th>
            <Th>Status</Th>
            <Th>Created</Th>
            <Th className="text-right">Actions</Th>
          </tr>
        }
        footer={<Pagination total={data?.total ?? 0} paged={paged} />}
      >
        {data?.items.map((t) => <TripRow key={t.id} trip={t} />)}
      </TableCard>
    </>
  )
}

function TripRow({ trip }: { trip: AdminTrip }) {
  const update = useUpdateTrip()
  const remove = useDeleteTrip()
  const replan = useReplanTrip()
  const [editing, setEditing] = useState(false)
  const busy = update.isPending || remove.isPending || replan.isPending

  return (
    <Fragment>
    <tr className={trip.status === 'failed' ? 'bg-red-50/50' : undefined}>
      <Td>
        <span className="block font-medium">{trip.destination}</span>
        <span className="block text-xs text-slate-500">
          {formatDay(trip.start_date)} – {formatDay(trip.end_date)}
        </span>
        <span className="block text-xs text-slate-500">
          {trip.travelers} traveller{trip.travelers > 1 ? 's' : ''} · ₹{Math.round(trip.budget).toLocaleString('en-IN')}
        </span>
        {trip.member_count > 1 && (
          <span className="block text-xs text-slate-500">{trip.member_count} travellers</span>
        )}
      </Td>
      <Td className="text-xs text-slate-600">{trip.owner_email}</Td>
      <Td>
        <div className="flex flex-col items-start gap-1">
          <StatusBadge status={trip.status} />
          <TripStatusSelects id={trip.id} status={trip.status} planStatus={trip.plan_status} />
          {trip.error && (
            <span className="block max-w-xs text-xs text-red-700" title={trip.error}>
              {trip.error.slice(0, 90)}
            </span>
          )}
        </div>
      </Td>
      <Td className="text-xs text-slate-500">{formatWhen(trip.created_at)}</Td>
      <Td className="text-right">
        <div className="flex flex-wrap justify-end gap-1">
          <Button onClick={() => setEditing((v) => !v)}>{editing ? 'Close' : 'Edit'}</Button>
          <Button disabled={busy || trip.status === 'processing'} onClick={() => replan.mutate(trip.id)}>
            Replan
          </Button>
          {/* A trip stuck in "processing" because a worker died is the common
              case here: marking it failed lets the owner replan it. */}
          {trip.status === 'processing' && (
            <Button
              disabled={busy}
              onClick={() => update.mutate({ id: trip.id, patch: { status: 'failed' } })}
            >
              Mark failed
            </Button>
          )}
          <ConfirmButton
            disabled={busy}
            confirmLabel="Delete for good"
            onConfirm={() => remove.mutate(trip.id)}
          >
            Delete
          </ConfirmButton>
        </div>
        <ErrorNote error={update.error ?? remove.error ?? replan.error} fallback="That change did not go through." />
      </Td>
    </tr>
    {editing && (
      <tr>
        <td colSpan={5} className="px-4 pb-4">
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
        </td>
      </tr>
    )}
    </Fragment>
  )
}
