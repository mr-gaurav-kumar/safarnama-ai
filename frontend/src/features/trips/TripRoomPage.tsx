import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { getAccessToken, refreshSession } from '@/lib/api'
import { useTrip } from '@/features/trips/api'
import { useMembers } from '@/features/trips/groupApi'
import { useAuth } from '@/lib/auth'

interface RoomMessage {
  id: string
  user_id: string
  name: string
  text: string
  created_at: string
}

type Status = 'connecting' | 'open' | 'closed' | 'gone'

/** The group's live discussion for one trip. */
export function TripRoomPage() {
  const { id = '' } = useParams<{ id: string }>()
  const { data: trip } = useTrip(id)
  const { data: members } = useMembers(id)
  const qc = useQueryClient()
  const [messages, setMessages] = useState<RoomMessage[]>([])
  const [status, setStatus] = useState<Status>('connecting')
  const [draft, setDraft] = useState('')
  const [notice, setNotice] = useState<string | null>(null)
  const socket = useRef<WebSocket | null>(null)
  const log = useRef<HTMLDivElement>(null)
  const { user } = useAuth()

  useEffect(() => {
    let stopped = false
    let retried = false

    function connect() {
      const token = getAccessToken()
      if (!token) return setStatus('closed')
      const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${scheme}://${window.location.host}/api/ws/trips/${id}/room`)
      socket.current = ws
      ws.onopen = () => ws.send(JSON.stringify({ type: 'auth', token }))
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data as string)
        if (data.type === 'history') {
          setMessages(data.messages)
          setStatus('open')
        } else if (data.type === 'message') {
          setMessages((prev) => (prev.some((m) => m.id === data.message.id) ? prev : [...prev, data.message]))
        } else if (data.type === 'members_changed') {
          void qc.invalidateQueries({ queryKey: ['trips', id, 'members'] })
        } else if (data.type === 'error') {
          setNotice(data.detail)
        }
      }
      ws.onclose = (e) => {
        if (stopped) return
        if (e.code === 4401 && !retried) {
          retried = true
          void refreshSession().then((u) => (u && !stopped ? connect() : setStatus('closed')))
          return
        }
        setStatus(e.code === 4404 ? 'gone' : 'closed')
      }
    }

    connect()
    return () => {
      stopped = true
      socket.current?.close()
    }
  }, [id, qc])

  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight })
  }, [messages])

  function send(e: FormEvent) {
    e.preventDefault()
    const text = draft.trim()
    if (!text || socket.current?.readyState !== WebSocket.OPEN) return
    setNotice(null)
    socket.current.send(JSON.stringify({ type: 'message', text }))
    setDraft('')
  }

  const joined = (members ?? []).filter((m) => m.role === 'owner' || m.role === 'member')

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_16rem]">
      <section className="flex h-[70vh] flex-col rounded-lg border border-slate-200 bg-white">
        <header className="border-b border-slate-100 px-5 py-3">
          <h1 className="text-lg font-semibold">{trip ? `${trip.destination} trip room` : 'Trip room'}</h1>
          <p className="text-xs text-slate-500">
            {status === 'open' && 'Live — everyone on the trip sees this'}
            {status === 'connecting' && 'Connecting…'}
            {status === 'closed' && 'Disconnected — reload to reconnect'}
            {status === 'gone' && "You're not on this trip any more"}
          </p>
        </header>

        <div ref={log} role="log" aria-live="polite" className="flex-1 space-y-3 overflow-y-auto px-5 py-4 text-sm">
          {status === 'open' && messages.length === 0 && (
            <p className="text-slate-500">No messages yet. Say which day you want the beach!</p>
          )}
          {messages.map((m) => {
            const mine = m.user_id === user?.id
            return (
              <div key={m.id} className={mine ? 'text-right' : ''}>
                <span className="block text-xs text-slate-500">{m.name}</span>
                <p
                  className={`inline-block max-w-[80%] whitespace-pre-wrap break-words rounded-2xl px-3 py-2 text-left ${
                    mine ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-900'
                  }`}
                >
                  {m.text}
                </p>
              </div>
            )
          })}
        </div>

        {notice && <p role="alert" className="px-5 pb-2 text-xs text-red-700">{notice}</p>}

        <form onSubmit={send} className="flex gap-2 border-t border-slate-100 p-3">
          <label htmlFor="room-input" className="sr-only">Message</label>
          <input
            id="room-input"
            value={draft}
            maxLength={1000}
            onChange={(e) => setDraft(e.target.value)}
            disabled={status !== 'open'}
            placeholder="Message the group…"
            className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900 disabled:bg-slate-50"
          />
          <button
            type="submit"
            disabled={status !== 'open' || !draft.trim()}
            className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            Send
          </button>
        </form>
      </section>

      <aside className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
        <h2 className="mb-2 font-medium">On this trip</h2>
        <ul className="space-y-2">
          {joined.map((m) => (
            <li key={m.id ?? 'owner'}>
              <span className="font-medium">{m.name}</span>
              {m.is_you && <span className="text-slate-500"> (you)</span>}
              <span className="block text-xs text-slate-500">
                {m.style_tags.length ? m.style_tags.join(', ') : 'no preference yet'}
              </span>
            </li>
          ))}
        </ul>
        <Link to={`/trips/${id}`} className="mt-4 inline-block text-slate-600 underline">
          Back to the plan
        </Link>
      </aside>
    </div>
  )
}
