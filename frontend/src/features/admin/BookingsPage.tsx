import { useState } from 'react'
import { formatDay, formatWhen, useAdminBookings, useDeleteBooking, useUpdateBooking } from './api'
import {
  Button, ConfirmButton, ErrorNote, Filter, PageHeader, Pagination, StatusBadge, TableCard, Td, Th, usePaged,
} from './ui'
import type { BookingStatus, PackageBooking } from './types'

const STATUSES = [
  { value: '', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'cancelled', label: 'Cancelled' },
]
const INR = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

export function BookingsPage() {
  const [status, setStatus] = useState('pending')
  const paged = usePaged(25)
  const { data, isPending, isError } = useAdminBookings(status, paged.limit, paged.offset)

  return (
    <>
      <PageHeader title="Package bookings" subtitle="Travellers who opted into a package. Confirm or cancel each one." />
      <Filter label="Status" value={status} onChange={(v) => { setStatus(v); paged.reset() }} options={STATUSES} />
      <TableCard
        colSpan={5}
        isPending={isPending}
        isError={isError}
        isEmpty={data?.items.length === 0}
        emptyText="No bookings here."
        head={
          <tr>
            <Th>Traveller</Th>
            <Th>Package</Th>
            <Th>Dates</Th>
            <Th>Status</Th>
            <Th className="text-right">Actions</Th>
          </tr>
        }
        footer={<Pagination total={data?.total ?? 0} paged={paged} />}
      >
        {data?.items.map((b) => <BookingRow key={b.id} booking={b} />)}
      </TableCard>
    </>
  )
}

function BookingRow({ booking: b }: { booking: PackageBooking }) {
  const update = useUpdateBooking()
  const remove = useDeleteBooking()
  const busy = update.isPending || remove.isPending
  const set = (status: BookingStatus) => update.mutate({ id: b.id, status })
  return (
    <tr>
      <Td>
        <span className="block font-medium">{b.user_name}</span>
        <span className="block text-xs text-slate-500">{b.user_email}</span>
        <span className="block text-xs text-slate-400">Booked {formatWhen(b.created_at)}</span>
      </Td>
      <Td>
        <span className="block font-medium">{b.package_title}</span>
        <span className="block text-xs text-slate-500">
          {b.travelers} traveller{b.travelers > 1 ? 's' : ''} · {INR.format(b.total_price)}
        </span>
        {b.note && <span className="block max-w-xs text-xs text-slate-500">“{b.note}”</span>}
      </Td>
      <Td className="text-xs text-slate-600">
        {formatDay(b.start_date)} – {formatDay(b.end_date)}
      </Td>
      <Td><StatusBadge status={b.status} /></Td>
      <Td className="text-right">
        <div className="flex flex-wrap justify-end gap-1">
          {b.status !== 'confirmed' && <Button disabled={busy} onClick={() => set('confirmed')}>Confirm</Button>}
          {b.status !== 'cancelled' && <Button disabled={busy} onClick={() => set('cancelled')}>Cancel</Button>}
          {b.status === 'cancelled' && <Button disabled={busy} onClick={() => set('pending')}>Reopen</Button>}
          <ConfirmButton disabled={busy} confirmLabel="Delete" onConfirm={() => remove.mutate(b.id)}>Delete</ConfirmButton>
        </div>
        <ErrorNote error={update.error ?? remove.error} fallback="That change did not go through." />
      </Td>
    </tr>
  )
}
