import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiErrorMessage } from '@/lib/auth'
import { formatDate } from '@/features/trips/api'
import {
  useInvite, useLeave, useMatches, useMembers, useRemoveMember, useReplan,
  useRequestMatch, useSetDiscoverable, useSetPreferences,
} from '@/features/trips/groupApi'
import { STYLE_TAGS, type StyleTag, type TripDetail } from '@/features/trips/types'

/** Who is on the trip, what each wants, and (for the organiser) inviting people. */
export function GroupPanel({ trip }: { trip: TripDetail }) {
  const isOwner = trip.role === 'owner'
  const { data: members } = useMembers(trip.id)
  const joined = (members ?? []).filter((m) => m.role === 'owner' || m.role === 'member')
  const pending = (members ?? []).filter((m) => m.role === 'invited' || m.role === 'declined')
  const me = members?.find((m) => m.is_you)

  return (
    <section className="space-y-5 rounded-lg border border-slate-200 bg-white p-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-medium">Travelling together</h2>
          <p className="text-sm text-slate-600">
            {joined.length > 1
              ? `${joined.length} people — the plan balances everyone's preferences.`
              : 'Invite friends; the plan will balance what everyone wants.'}
          </p>
        </div>
        {joined.length > 1 && (
          <Link
            to={`/trips/${trip.id}/room`}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50"
          >
            Open trip room
          </Link>
        )}
      </header>

      <ul className="divide-y divide-slate-100 text-sm">
        {joined.map((m) => (
          <MemberRow key={m.id ?? 'owner'} tripId={trip.id} member={m} canRemove={isOwner} />
        ))}
      </ul>

      {me && <MyPreferences tripId={trip.id} initial={me.style_tags as StyleTag[]} />}

      {isOwner && <InviteForm tripId={trip.id} />}

      {isOwner && pending.length > 0 && (
        <div className="text-sm">
          <h3 className="mb-1 font-medium text-slate-700">Invitations</h3>
          <ul className="space-y-1">
            {pending.map((m) => (
              <li key={m.id} className="flex items-center justify-between gap-3 text-slate-600">
                <span className="truncate">{m.email}</span>
                <span className="text-xs">{m.role === 'invited' ? 'waiting' : 'declined'}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {isOwner ? <OwnerActions trip={trip} groupSize={joined.length} /> : <LeaveButton tripId={trip.id} />}

      {isOwner && <FindTravellers trip={trip} />}
    </section>
  )
}

function MemberRow({ tripId, member, canRemove }: { tripId: string; member: { id: string | null; name: string | null; email: string; role: string; style_tags: string[]; is_you: boolean }; canRemove: boolean }) {
  const remove = useRemoveMember(tripId)
  return (
    <li className="flex flex-wrap items-center gap-3 py-2">
      <span className="font-medium">
        {member.name ?? member.email}
        {member.is_you && <span className="ml-1 font-normal text-slate-500">(you)</span>}
      </span>
      {member.role === 'owner' && (
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">organiser</span>
      )}
      <span className="flex-1 text-slate-500">
        {member.style_tags.length ? member.style_tags.join(', ') : 'no preference yet'}
      </span>
      {canRemove && member.role === 'member' && member.id && (
        <button
          onClick={() => remove.mutate(member.id!)}
          disabled={remove.isPending}
          className="text-xs text-slate-500 hover:text-red-700"
        >
          Remove
        </button>
      )}
    </li>
  )
}

function MyPreferences({ tripId, initial }: { tripId: string; initial: StyleTag[] }) {
  const [tags, setTags] = useState<StyleTag[]>(initial)
  const save = useSetPreferences(tripId)
  useEffect(() => setTags(initial), [initial.join(',')]) // eslint-disable-line react-hooks/exhaustive-deps
  const changed = tags.join(',') !== initial.join(',')

  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-slate-700">What you want from this trip</h3>
      <div className="flex flex-wrap items-center gap-2">
        {STYLE_TAGS.map((tag) => {
          const on = tags.includes(tag)
          return (
            <button
              key={tag}
              type="button"
              aria-pressed={on}
              onClick={() => setTags((t) => (on ? t.filter((x) => x !== tag) : [...t, tag]))}
              className={`rounded-full border px-3 py-1 text-xs capitalize ${
                on ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-300 text-slate-700'
              }`}
            >
              {tag}
            </button>
          )
        })}
        {changed && (
          <button
            onClick={() => save.mutate(tags)}
            disabled={save.isPending}
            className="rounded bg-slate-900 px-3 py-1 text-xs font-medium text-white disabled:opacity-50"
          >
            {save.isPending ? 'Saving…' : 'Save'}
          </button>
        )}
      </div>
    </div>
  )
}

function InviteForm({ tripId }: { tripId: string }) {
  const [email, setEmail] = useState('')
  const [note, setNote] = useState<string | null>(null)
  const invite = useInvite(tripId)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setNote(null)
    try {
      const res = await invite.mutateAsync(email.trim())
      setNote(res.detail)
      setEmail('')
    } catch (err) {
      setNote(apiErrorMessage(err, 'Could not send the invitation.'))
    }
  }

  return (
    <form onSubmit={submit} className="text-sm">
      <label htmlFor="invite-email" className="mb-1 block font-medium text-slate-700">
        Invite by email
      </label>
      <div className="flex gap-2">
        <input
          id="invite-email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="friend@example.com"
          className="min-w-0 flex-1 rounded border border-slate-300 px-3 py-1.5 outline-none focus:border-slate-900"
        />
        <button
          type="submit"
          disabled={invite.isPending}
          className="rounded bg-slate-900 px-3 py-1.5 font-medium text-white disabled:opacity-50"
        >
          Invite
        </button>
      </div>
      {note && <p className="mt-1 text-slate-600">{note}</p>}
    </form>
  )
}

function OwnerActions({ trip, groupSize }: { trip: TripDetail; groupSize: number }) {
  const replan = useReplan(trip.id)
  if (groupSize < 2) return null
  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <button
        onClick={() => replan.mutate()}
        disabled={replan.isPending || trip.status === 'processing'}
        className="rounded border border-slate-300 px-3 py-1.5 hover:bg-slate-50 disabled:opacity-50"
      >
        {trip.status === 'processing' ? 'Replanning…' : 'Replan for the group'}
      </button>
      <span className="text-slate-500">Uses everyone's latest preferences.</span>
    </div>
  )
}

function LeaveButton({ tripId }: { tripId: string }) {
  const leave = useLeave(tripId)
  const navigate = useNavigate()
  return (
    <button
      onClick={() => leave.mutate(undefined, { onSuccess: () => navigate('/dashboard') })}
      disabled={leave.isPending}
      className="text-sm text-slate-500 hover:text-red-700"
    >
      Leave this trip
    </button>
  )
}

function FindTravellers({ trip }: { trip: TripDetail }) {
  const toggle = useSetDiscoverable(trip.id)
  const { data: matches } = useMatches(trip.id, trip.discoverable)
  const request = useRequestMatch(trip.id)
  const [note, setNote] = useState<string | null>(null)

  return (
    <div className="border-t border-slate-100 pt-4 text-sm">
      <label className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={trip.discoverable}
          onChange={(e) => toggle.mutate(e.target.checked)}
          className="mt-0.5"
        />
        <span>
          <span className="font-medium">Let other travellers find this trip</span>
          <span className="block text-slate-600">
            People going to {trip.destination} on overlapping dates who also turned this on
            will see your first name and dates — nothing else — and can suggest teaming up.
          </span>
        </span>
      </label>

      {trip.discoverable && matches && matches.length > 0 && (
        <ul className="mt-3 space-y-2">
          {matches.map((m) => (
            <li key={m.trip_id} className="flex flex-wrap items-center justify-between gap-2 rounded border border-slate-200 px-3 py-2">
              <span>
                <b>{m.first_name}</b> · {formatDate(m.start_date)} – {formatDate(m.end_date)} ·{' '}
                {m.overlap_days} day{m.overlap_days > 1 ? 's' : ''} overlap
              </span>
              {m.already_requested ? (
                <span className="text-xs text-slate-500">Suggested</span>
              ) : (
                <button
                  onClick={async () => {
                    try {
                      const r = await request.mutateAsync(m.trip_id)
                      setNote(r.detail)
                    } catch (err) {
                      setNote(apiErrorMessage(err, 'Could not send that.'))
                    }
                  }}
                  className="rounded border border-slate-300 px-2.5 py-1 text-xs hover:bg-slate-50"
                  title="Shares your first name and email with them"
                >
                  Suggest teaming up
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {trip.discoverable && matches && matches.length === 0 && (
        <p className="mt-2 text-slate-500">No one else has an overlapping {trip.destination} trip yet.</p>
      )}
      {note && <p className="mt-2 text-slate-600">{note}</p>}
      <p className="mt-2 text-xs text-slate-500">
        “Suggest teaming up” shares your first name and email with them.
      </p>
    </div>
  )
}
