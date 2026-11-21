import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { formatWhen, useChatLogs } from './api'
import {
  Badge, Button, PageHeader, Pagination, SearchBox, TableCard, Td, Th,
  useDebounced, usePaged,
} from './ui'
import type { AdminChatLine } from './types'

export function ChatLogsPage() {
  // Escalations link here with ?email=..., so "full conversation" lands on
  // that person's messages already filtered.
  const [searchParams, setSearchParams] = useSearchParams()
  const email = searchParams.get('email') ?? ''

  const [search, setSearch] = useState('')
  const q = useDebounced(search)
  const paged = usePaged(50)

  const { data, isPending, isError } = useChatLogs(q, email, paged.limit, paged.offset)

  return (
    <>
      <PageHeader
        title="Chat logs"
        subtitle="Every support message, newest first."
      />

      <div className="flex flex-wrap items-center gap-3">
        <SearchBox
          value={search}
          onChange={(v) => { setSearch(v); paged.reset() }}
          placeholder="Search message text"
        />
        {email && (
          <span className="flex items-center gap-2 rounded bg-slate-100 px-3 py-1.5 text-sm">
            {email}
            <Button onClick={() => { setSearchParams({}); paged.reset() }}>Clear</Button>
          </span>
        )}
      </div>

      <TableCard
        colSpan={4}
        isPending={isPending}
        isError={isError}
        isEmpty={data?.items.length === 0}
        emptyText="No messages match that."
        head={
          <tr>
            <Th className="w-24">From</Th>
            <Th>Message</Th>
            <Th className="w-44">Read as</Th>
            <Th className="w-44">When</Th>
          </tr>
        }
        footer={<Pagination total={data?.total ?? 0} paged={paged} />}
      >
        {data?.items.map((line) => (
          <ChatRow key={line.id} line={line} onPickEmail={(e) => { setSearchParams({ email: e }); paged.reset() }} />
        ))}
      </TableCard>
    </>
  )
}

function ChatRow({
  line,
  onPickEmail,
}: {
  line: AdminChatLine
  onPickEmail: (email: string) => void
}) {
  const fromUser = line.sender === 'user'

  return (
    <tr className={fromUser ? undefined : 'bg-slate-50/60'}>
      <Td>
        <Badge tone={fromUser ? 'info' : 'neutral'}>{line.sender}</Badge>
        <button
          onClick={() => onPickEmail(line.user_email)}
          className="mt-1 block max-w-[8rem] truncate text-xs text-slate-500 underline hover:text-slate-900"
          title={line.user_email}
        >
          {line.user_email}
        </button>
      </Td>
      <Td className="max-w-lg whitespace-pre-wrap text-slate-800">{line.message}</Td>
      <Td>
        <div className="flex flex-wrap gap-1">
          {line.intent && <Badge>{line.intent}</Badge>}
          {line.sentiment && (
            <Badge
              tone={
                line.sentiment === 'negative' ? 'bad'
                  : line.sentiment === 'positive' ? 'good'
                    : 'neutral'
              }
            >
              {line.sentiment}
            </Badge>
          )}
          {!line.intent && !line.sentiment && <span className="text-xs text-slate-400">--</span>}
        </div>
      </Td>
      <Td className="text-xs text-slate-500">{formatWhen(line.created_at)}</Td>
    </tr>
  )
}
