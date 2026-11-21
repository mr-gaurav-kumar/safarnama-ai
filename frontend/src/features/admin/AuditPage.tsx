import { formatWhen, useAudit } from './api'
import { Badge, PageHeader, Pagination, TableCard, Td, Th, usePaged } from './ui'
import type { AuditLine } from './types'

/** Verbs in plain words. Anything unmapped falls back to the raw action name,
 *  so a new admin route still renders a readable row. */
const ACTIONS: Record<string, string> = {
  'user.create': 'created an account',
  'user.update': 'changed an account',
  'user.delete': 'deleted an account',
  'trip.update': 'changed a trip',
  'trip.delete': 'deleted a trip',
  'flag.review': 'reviewed a fraud flag',
  'escalation.update': 'updated an escalation',
  'feedback.delete': 'deleted feedback',
}

const DESTRUCTIVE = new Set(['user.delete', 'trip.delete', 'feedback.delete'])

export function AuditPage() {
  const paged = usePaged(50)
  const { data, isPending, isError } = useAudit(paged.limit, paged.offset)

  return (
    <>
      <PageHeader
        title="Audit log"
        subtitle="Every admin change, newest first. Written by the server, not editable here."
      />

      <TableCard
        colSpan={4}
        isPending={isPending}
        isError={isError}
        isEmpty={data?.items.length === 0}
        emptyText="No admin actions recorded yet."
        head={
          <tr>
            <Th>Admin</Th>
            <Th>Did what</Th>
            <Th>Details</Th>
            <Th className="w-44">When</Th>
          </tr>
        }
        footer={<Pagination total={data?.total ?? 0} paged={paged} />}
      >
        {data?.items.map((line) => <AuditRow key={line.id} line={line} />)}
      </TableCard>
    </>
  )
}

function AuditRow({ line }: { line: AuditLine }) {
  const details = Object.entries(line.details ?? {})

  return (
    <tr>
      <Td className="text-xs text-slate-700">
        {line.admin_email ?? <span className="text-slate-400">deleted admin</span>}
      </Td>
      <Td>
        <span className="block">{ACTIONS[line.action] ?? line.action}</span>
        <span className="mt-0.5 block text-xs text-slate-400">
          {line.target_type} · <code>{line.target_id.slice(0, 8)}</code>
        </span>
        {DESTRUCTIVE.has(line.action) && <Badge tone="bad">destructive</Badge>}
      </Td>
      <Td>
        {details.length === 0 ? (
          <span className="text-xs text-slate-400">--</span>
        ) : (
          <dl className="space-y-0.5 text-xs">
            {details.map(([k, v]) => (
              <div key={k} className="flex gap-2">
                <dt className="shrink-0 text-slate-500">{k}</dt>
                <dd className="break-all text-slate-800">{JSON.stringify(v)}</dd>
              </div>
            ))}
          </dl>
        )}
      </Td>
      <Td className="text-xs text-slate-500">{formatWhen(line.created_at)}</Td>
    </tr>
  )
}
