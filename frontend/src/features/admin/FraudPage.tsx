import { useState } from 'react'
import { formatWhen, useFlags, useReviewFlag } from './api'
import {
  Badge, Button, ErrorNote, Filter, PageHeader, Pagination, StatusBadge,
  TableCard, Td, Th, usePaged,
} from './ui'
import type { AdminFlag } from './types'

const STATUSES = [
  { value: 'open', label: 'Open' },
  { value: 'resolved', label: 'Confirmed' },
  { value: 'dismissed', label: 'Dismissed' },
  { value: '', label: 'All' },
]

/** The rule names in app/fraud/scorer.py, in words an admin can act on. */
const REASONS: Record<string, string> = {
  trip_burst: '5+ trips created within 10 minutes',
  invite_burst: '10+ invitations sent within an hour',
  many_accounts_one_ip: '3+ accounts signed up from one IP in 24h',
  login_failures: '5+ failed logins within 15 minutes',
  ip_hopping: 'Logins from 4+ different IPs within an hour',
  anomalous_activity: 'Unusual mix of behaviour (Isolation Forest)',
}

export function FraudPage() {
  const [status, setStatus] = useState('open')
  const paged = usePaged(25)
  const { data, isPending, isError } = useFlags(status, paged.limit, paged.offset)

  return (
    <>
      <PageHeader
        title="Fraud review"
        subtitle="Highest risk first. Confirming a flag can block the account in the same step."
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
        emptyText={status === 'open' ? 'Nothing waiting for review.' : 'Nothing here.'}
        head={
          <tr>
            <Th className="w-28">Risk</Th>
            <Th>Account</Th>
            <Th>Why it fired</Th>
            <Th>State</Th>
            <Th className="text-right">Decision</Th>
          </tr>
        }
        footer={<Pagination total={data?.total ?? 0} paged={paged} />}
      >
        {data?.items.map((f) => <FlagRow key={f.id} flag={f} />)}
      </TableCard>
    </>
  )
}

function RiskMeter({ score }: { score: number }) {
  const pct = Math.round(Math.min(Math.max(score, 0), 1) * 100)
  // Three bands, because a reviewer decides by band, not by decimal.
  const tone = pct >= 70 ? 'bg-red-600' : pct >= 40 ? 'bg-amber-500' : 'bg-slate-400'
  return (
    <div>
      <span className="block text-lg font-semibold tabular-nums">{score.toFixed(2)}</span>
      <span className="mt-1 block h-1.5 w-20 overflow-hidden rounded-full bg-slate-200">
        <span className={`block h-full ${tone}`} style={{ width: `${pct}%` }} />
      </span>
    </div>
  )
}

function FlagRow({ flag }: { flag: AdminFlag }) {
  const review = useReviewFlag()
  const [open, setOpen] = useState(false)
  const isOpen = flag.status === 'open'
  const details = Object.entries(flag.details ?? {})

  return (
    <tr className={flag.risk_score >= 0.7 && isOpen ? 'bg-red-50/50' : undefined}>
      <Td><RiskMeter score={flag.risk_score} /></Td>
      <Td>
        <span className="block text-xs text-slate-700">{flag.user_email}</span>
        {flag.user_blocked && <Badge tone="bad">account blocked</Badge>}
        <span className="mt-1 block text-xs text-slate-400">{formatWhen(flag.created_at)}</span>
      </Td>
      <Td>
        <span className="block">{REASONS[flag.reason] ?? flag.reason}</span>
        <code className="mt-0.5 block text-xs text-slate-400">{flag.reason}</code>
        {details.length > 0 && (
          <>
            <button
              onClick={() => setOpen((v) => !v)}
              className="mt-1 text-xs text-slate-600 underline hover:text-slate-900"
            >
              {open ? 'Hide evidence' : `Evidence (${details.length})`}
            </button>
            {open && (
              <dl className="mt-2 space-y-0.5 rounded bg-slate-50 p-2 text-xs">
                {details.map(([k, v]) => (
                  <div key={k} className="flex gap-2">
                    <dt className="shrink-0 text-slate-500">{k}</dt>
                    <dd className="break-all text-slate-800">{JSON.stringify(v)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </>
        )}
      </Td>
      <Td>
        <StatusBadge status={flag.status} />
        {flag.reviewed_at && (
          <span className="mt-1 block text-xs text-slate-400">{formatWhen(flag.reviewed_at)}</span>
        )}
      </Td>
      <Td className="text-right">
        {isOpen ? (
          <div className="flex flex-wrap justify-end gap-1">
            <Button
              disabled={review.isPending}
              onClick={() => review.mutate({ id: flag.id, patch: { status: 'dismissed', block_user: false } })}
            >
              False positive
            </Button>
            <Button
              disabled={review.isPending}
              onClick={() => review.mutate({ id: flag.id, patch: { status: 'resolved', block_user: false } })}
            >
              Confirm
            </Button>
            <Button
              variant="danger"
              disabled={review.isPending || flag.user_blocked}
              onClick={() => review.mutate({ id: flag.id, patch: { status: 'resolved', block_user: true } })}
            >
              Confirm + block
            </Button>
          </div>
        ) : (
          <Button
            disabled={review.isPending}
            onClick={() => review.mutate({ id: flag.id, patch: { status: 'open', block_user: false } })}
          >
            Reopen
          </Button>
        )}
        <ErrorNote error={review.error} fallback="Could not record that decision." />
      </Td>
    </tr>
  )
}
