import { useState } from 'react'
import { Link } from 'react-router-dom'
import { formatWhen, useEscalations, useUpdateEscalation } from './api'
import {
  Badge, Button, ErrorNote, Filter, PageHeader, Pagination, StatusBadge,
  TableCard, Td, Th, usePaged,
} from './ui'
import type { AdminEscalation } from './types'

const STATUSES = [
  { value: 'open', label: 'Open' },
  { value: 'resolved', label: 'Resolved' },
  { value: '', label: 'All' },
]

const REASONS: Record<string, string> = {
  negative_sentiment: 'The person sounded upset',
  repeated_issue: 'Asked about the same problem repeatedly',
}

export function EscalationsPage() {
  const [status, setStatus] = useState('open')
  const paged = usePaged(25)
  const { data, isPending, isError } = useEscalations(status, paged.limit, paged.offset)

  return (
    <>
      <PageHeader
        title="Support escalations"
        subtitle="Chats the bot handed over. One open escalation per person at a time."
      >
        <Filter
          label="Show"
          value={status}
          onChange={(v) => { setStatus(v); paged.reset() }}
          options={STATUSES}
        />
      </PageHeader>

      <TableCard
        colSpan={5}
        isPending={isPending}
        isError={isError}
        isEmpty={data?.items.length === 0}
        emptyText={status === 'open' ? 'Nobody is waiting.' : 'Nothing here.'}
        head={
          <tr>
            <Th>Person</Th>
            <Th>Reason</Th>
            <Th>What they said</Th>
            <Th>State</Th>
            <Th className="text-right">Actions</Th>
          </tr>
        }
        footer={<Pagination total={data?.total ?? 0} paged={paged} />}
      >
        {data?.items.map((e) => <EscalationRow key={e.id} escalation={e} />)}
      </TableCard>
    </>
  )
}

function EscalationRow({ escalation }: { escalation: AdminEscalation }) {
  const update = useUpdateEscalation()
  const isOpen = escalation.status === 'open'

  return (
    <tr className={isOpen ? 'bg-amber-50/50' : undefined}>
      <Td>
        <span className="block text-xs text-slate-700">{escalation.user_email}</span>
        <span className="mt-1 block text-xs text-slate-400">{formatWhen(escalation.created_at)}</span>
      </Td>
      <Td>
        <span className="block">{REASONS[escalation.reason] ?? escalation.reason}</span>
        {escalation.intent && <Badge tone="info">{escalation.intent}</Badge>}
      </Td>
      <Td>
        <blockquote className="max-w-md border-l-2 border-slate-300 pl-3 text-slate-700 italic">
          {escalation.excerpt}
        </blockquote>
        <Link
          to={`/admin/chat-logs?email=${encodeURIComponent(escalation.user_email)}`}
          className="mt-1 inline-block text-xs text-slate-600 underline hover:text-slate-900"
        >
          Full conversation
        </Link>
      </Td>
      <Td><StatusBadge status={escalation.status} /></Td>
      <Td className="text-right">
        <Button
          disabled={update.isPending}
          onClick={() =>
            update.mutate({ id: escalation.id, status: isOpen ? 'resolved' : 'open' })
          }
        >
          {isOpen ? 'Mark resolved' : 'Reopen'}
        </Button>
        <ErrorNote error={update.error} fallback="Could not update that." />
      </Td>
    </tr>
  )
}
