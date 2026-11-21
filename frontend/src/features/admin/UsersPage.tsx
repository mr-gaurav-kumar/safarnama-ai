import { useState } from 'react'
import { Avatar } from '@/components/Avatar'
import { useAuth } from '@/lib/auth'
import {
  formatWhen, useCreateUser, useDeleteUser, useUpdateUser, useUsers,
} from './api'
import {
  Badge, Button, ConfirmButton, ErrorNote, PageHeader, Pagination, SearchBox,
  TableCard, Td, Th, useDebounced, usePaged,
} from './ui'
import type { AdminUser } from './types'
import { UserDrawer } from './UserDrawer'

export function UsersPage() {
  const [search, setSearch] = useState('')
  const q = useDebounced(search)
  const paged = usePaged(25)
  const [creating, setCreating] = useState(false)
  const [openId, setOpenId] = useState<string | null>(null)

  const { data, isPending, isError } = useUsers(q, paged.limit, paged.offset)

  return (
    <>
      <PageHeader title="Users" subtitle="Every account. Click a user to see their full profile and trips.">
        <Button variant="primary" onClick={() => setCreating((v) => !v)}>
          {creating ? 'Close' : 'Add user'}
        </Button>
      </PageHeader>

      {creating && <CreateUserForm onDone={() => setCreating(false)} />}

      <SearchBox
        value={search}
        onChange={(v) => { setSearch(v); paged.reset() }}
        placeholder="Name or email"
      />

      <TableCard
        colSpan={6}
        isPending={isPending}
        isError={isError}
        isEmpty={data?.items.length === 0}
        emptyText={q ? 'No user matches that.' : 'No users yet.'}
        head={
          <tr>
            <Th>User</Th>
            <Th>Role</Th>
            <Th>State</Th>
            <Th className="text-right">Trips</Th>
            <Th className="text-right">Flags</Th>
            <Th className="text-right">Actions</Th>
          </tr>
        }
        footer={<Pagination total={data?.total ?? 0} paged={paged} />}
      >
        {data?.items.map((u) => <UserRow key={u.id} user={u} onOpen={() => setOpenId(u.id)} />)}
      </TableCard>

      {openId && <UserDrawer userId={openId} onClose={() => setOpenId(null)} />}
    </>
  )
}

function UserRow({ user, onOpen }: { user: AdminUser; onOpen: () => void }) {
  const { user: me } = useAuth()
  const update = useUpdateUser()
  const remove = useDeleteUser()

  // The server refuses these on your own account so the last admin can never
  // lock everyone out. The UI says so instead of offering a button that 400s.
  const isSelf = me?.id === user.id
  const busy = update.isPending || remove.isPending

  return (
    <tr className={user.is_blocked ? 'bg-red-50/50' : undefined}>
      <Td>
        <div className="flex items-start gap-3">
          <Avatar name={user.name} url={user.avatar_url} className="h-9 w-9 text-xs" />
          <div className="min-w-0">
            <button onClick={onOpen} className="block text-left font-medium hover:underline">{user.name}</button>
            <span className="block text-xs text-slate-500">{user.email}</span>
            {user.home_town && <span className="block text-xs text-slate-500">{user.home_town}</span>}
            <span className="block text-xs text-slate-400">Joined {formatWhen(user.created_at)}</span>
          </div>
        </div>
      </Td>
      <Td>
        <Badge tone={user.role === 'admin' ? 'info' : 'neutral'}>{user.role}</Badge>
      </Td>
      <Td>
        <div className="flex flex-col gap-1">
          {user.is_blocked && <Badge tone="bad">blocked</Badge>}
          <Badge tone={user.is_verified ? 'good' : 'warn'}>
            {user.is_verified ? 'verified' : 'unverified'}
          </Badge>
        </div>
      </Td>
      <Td className="text-right tabular-nums">{user.trip_count}</Td>
      <Td className="text-right tabular-nums">
        {user.open_flags > 0 ? <Badge tone="warn">{user.open_flags}</Badge> : 0}
      </Td>
      <Td className="text-right">
        {isSelf ? (
          <div className="flex items-center justify-end gap-2">
            <span className="text-xs text-slate-500">This is you</span>
            <Button onClick={onOpen}>View</Button>
          </div>
        ) : (
          <div className="flex flex-wrap justify-end gap-1">
            <Button onClick={onOpen}>View</Button>
            <Button
              disabled={busy}
              onClick={() => update.mutate({ id: user.id, patch: { is_blocked: !user.is_blocked } })}
            >
              {user.is_blocked ? 'Unblock' : 'Block'}
            </Button>

            {!user.is_verified && (
              <Button
                disabled={busy}
                onClick={() => update.mutate({ id: user.id, patch: { is_verified: true } })}
              >
                Verify
              </Button>
            )}
            <ConfirmButton
              disabled={busy}
              confirmLabel="Delete for good"
              onConfirm={() => remove.mutate(user.id)}
            >
              Delete
            </ConfirmButton>
          </div>
        )}
        <ErrorNote error={update.error ?? remove.error} fallback="That change did not go through." />
      </Td>
    </tr>
  )
}

function CreateUserForm({ onDone }: { onDone: () => void }) {
  const create = useCreateUser()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [homeTown, setHomeTown] = useState('')
  const [phone, setPhone] = useState('')
  const [verified, setVerified] = useState(true)

  const field = 'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-900'

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        create.mutate(
          {
            name, email, password, is_verified: verified,
            home_town: homeTown.trim() || undefined, phone: phone.trim() || undefined,
          },
          { onSuccess: onDone },
        )
      }}
      className="space-y-4 rounded-lg border border-slate-200 bg-white p-5"
    >
      <p className="text-sm text-slate-600">
        Creates a traveller account directly -- no verification email is sent. New accounts are
        always travellers; there is a single admin.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1 text-sm">
          <span className="text-slate-600">Name</span>
          <input className={field} value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} />
        </label>
        <label className="space-y-1 text-sm">
          <span className="text-slate-600">Email</span>
          <input className={field} type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label className="space-y-1 text-sm">
          <span className="text-slate-600">Password</span>
          <input
            className={field} type="password" value={password} minLength={8} maxLength={72} pattern="(?=.*[A-Za-z])(?=.*\d).{8,}" title="At least 8 characters, with letters and numbers"
            onChange={(e) => setPassword(e.target.value)} required
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="text-slate-600">Home town</span>
          <input className={field} value={homeTown} onChange={(e) => setHomeTown(e.target.value)} maxLength={120} />
        </label>
        <label className="space-y-1 text-sm">
          <span className="text-slate-600">Mobile (optional)</span>
          <input className={field} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+91 98765 43210" />
        </label>
      </div>
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input type="checkbox" checked={verified} onChange={(e) => setVerified(e.target.checked)} />
        Mark the email as already verified
      </label>
      <ErrorNote error={create.error} fallback="Could not create that user." />
      <div className="flex gap-2">
        <Button type="submit" variant="primary" disabled={create.isPending}>
          {create.isPending ? 'Creating…' : 'Create user'}
        </Button>
        <Button onClick={onDone}>Cancel</Button>
      </div>
    </form>
  )
}
