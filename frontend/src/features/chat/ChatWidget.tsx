import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { apiErrorMessage, useAuth } from '@/lib/auth'
import { Icon } from '@/components/Icon'
import { useChat } from '@/features/chat/useChat'

const MAX_CHARS = 1000

/** Which help topic a URL belongs to -- the keys of backend/app/chat/pages.py. */
export function pageFor(pathname: string): string | null {
  if (pathname === '/login' || pathname === '/admin/login') return 'login'
  if (pathname === '/signup/business') return 'business_signup'
  if (pathname === '/signup' || pathname === '/verify') return 'signup'
  if (pathname === '/forgot-password' || pathname === '/reset-password') return 'forgot_password'
  if (pathname === '/') return 'home'
  if (pathname.startsWith('/profile')) return 'profile'
  if (pathname === '/trips/new') return 'new_trip'
  if (/^\/trips\/[^/]+\/packing/.test(pathname)) return 'packing'
  if (/^\/trips\/[^/]+\/room/.test(pathname)) return 'trip_room'
  if (/^\/trips\/[^/]+/.test(pathname)) return 'trip'
  if (pathname.startsWith('/assistant')) return 'assistant'
  if (pathname.startsWith('/recommend')) return 'recommend'
  if (pathname.startsWith('/book')) return 'book'
  if (pathname.startsWith('/dashboard')) return 'dashboard'
  if (pathname.startsWith('/packages')) return 'packages'
  if (pathname.startsWith('/insights')) return 'insights'
  return null
}

interface PageHelp {
  page: string | null
  title: string
  intro: string
  starters: string[]
}

/**
 * The floating Help chat. It knows which page it was opened on: the header
 * names it, the suggested questions are that page's, and the server answers
 * (and asks follow-up questions) about that page first.
 */
export function ChatWidget() {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()
  const page = pageFor(pathname)
  const { isAuthenticated } = useAuth()
  // Logged in: the live support chat. Logged out (login, sign-up, landing):
  // answers from the page's help notes, nothing saved -- see POST /chat/public.
  const live = useChat(open && isAuthenticated)
  const pub = usePublicHelp()
  const { messages, status, typing, notice, escalated } = isAuthenticated
    ? live
    : { ...pub, status: 'open' as const, escalated: false }
  const send = (text: string, pg: string | null) => (isAuthenticated ? live.send(text, pg) : pub.send(text, pg))
  const [draft, setDraft] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(true)
  const log = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLTextAreaElement>(null)
  const launcher = useRef<HTMLButtonElement>(null)

  const help = useQuery({
    queryKey: ['chat-help', page ?? 'general'],
    queryFn: async () => (await api.get<PageHelp>(`/chat/help/${page ?? 'general'}`)).data,
    enabled: open,
    staleTime: Infinity,
  })

  // A new page brings its own suggestions back into view.
  useEffect(() => setShowSuggestions(true), [page])

  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight })
  }, [messages, typing, open, help.data, showSuggestions])

  useEffect(() => {
    if (open) input.current?.focus()
  }, [open])

  function close() {
    setOpen(false)
    launcher.current?.focus()
  }

  function ask(text: string) {
    if (send(text, page)) {
      setDraft('')
      setShowSuggestions(false)
    }
  }

  function submit(event?: FormEvent) {
    event?.preventDefault()
    ask(draft)
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  const canSend = status === 'open' && draft.trim().length > 0
  const title = help.data?.title ?? 'Help'

  return (
    <>
      {open && (
        <section
          role="dialog"
          aria-label={page ? `Help with ${title}` : 'Help'}
          onKeyDown={(e) => e.key === 'Escape' && close()}
          className="fixed inset-x-3 bottom-20 z-50 flex max-h-[75vh] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_24px_60px_-20px_rgba(28,36,82,0.45)] sm:left-auto sm:right-4 sm:w-[400px]"
        >
          <header className="flex items-center gap-3 bg-[#1C2452] px-5 py-4 text-white">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/10 text-[#F2A93B]">
              <Icon name="compass" className="h-5 w-5" />
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="truncate text-[15px] font-semibold">{page ? `Help with ${title}` : 'Help'}</h2>
              <p className="text-xs text-white/65">
                {status === 'open' && (page ? 'Help with what’s on this page' : 'Ask about anything in the app')}
                {status === 'connecting' && 'Connecting…'}
                {status === 'reconnecting' && 'Reconnecting…'}
                {status === 'signed-out' && 'Please log in again to chat'}
              </p>
            </div>
            <button
              onClick={close}
              aria-label="Close help"
              className="rounded-lg p-1.5 text-white/70 hover:bg-white/10 hover:text-white"
            >
              <Icon name="close" className="h-4 w-4" />
            </button>
          </header>

          <div
            ref={log}
            role="log"
            aria-live="polite"
            className="flex-1 space-y-2.5 overflow-y-auto bg-slate-50/60 px-4 py-4 text-sm"
          >
            {messages.map((m) => (
              <p
                key={m.id}
                className={`max-w-[85%] whitespace-pre-wrap break-words rounded-2xl px-3.5 py-2.5 leading-relaxed ${
                  m.sender === 'user'
                    ? 'ml-auto rounded-br-md bg-[#1C2452] text-white'
                    : 'rounded-bl-md bg-white text-slate-800 ring-1 ring-slate-200'
                }`}
              >
                <span className="sr-only">{m.sender === 'user' ? 'You: ' : 'Help: '}</span>
                {m.message}
              </p>
            ))}

            {/* This page's welcome and questions: on open, and again on a new page. */}
            {help.data && showSuggestions && (
              <div className="space-y-2.5 pt-1">
                <p className="max-w-[85%] rounded-2xl rounded-bl-md bg-white px-3.5 py-2.5 leading-relaxed text-slate-800 ring-1 ring-slate-200">
                  {help.data.intro}
                </p>
                <div className="flex flex-col items-end gap-1.5">
                  {help.data.starters.map((q) => (
                    <button
                      key={q}
                      onClick={() => ask(q)}
                      disabled={status !== 'open'}
                      className="max-w-[90%] rounded-2xl border border-[#1C2452]/20 bg-white px-3.5 py-2 text-left text-[13px] text-[#1C2452] transition hover:border-[#1C2452]/50 hover:bg-[#1C2452]/5 disabled:opacity-50"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {typing && (
              <p className="flex items-center gap-1.5 text-xs text-slate-500">
                <span className="inline-flex gap-0.5">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.2s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.1s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
                </span>
                Help is typing
              </p>
            )}
          </div>

          {escalated && (
            <p className="border-t border-amber-100 bg-amber-50 px-4 py-2 text-xs text-amber-900">
              A person from our team has this conversation and will follow up by email.
            </p>
          )}
          {notice && (
            <p role="alert" className="border-t border-slate-100 px-4 py-2 text-xs text-red-700">
              {notice}
            </p>
          )}

          {!showSuggestions && help.data && (
            <button
              onClick={() => setShowSuggestions(true)}
              className="border-t border-slate-100 px-4 py-2 text-left text-xs font-medium text-[#1C2452] hover:bg-slate-50"
            >
              Show questions about {page ? title : 'the app'}
            </button>
          )}

          <form onSubmit={submit} className="flex items-end gap-2 border-t border-slate-100 bg-white p-3">
            <label className="sr-only" htmlFor="chat-input">Message</label>
            <textarea
              id="chat-input"
              ref={input}
              rows={1}
              value={draft}
              maxLength={MAX_CHARS}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={page ? `Ask about ${title.toLowerCase()}…` : 'Type a question…'}
              disabled={status !== 'open'}
              className="max-h-28 min-h-10 flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-[#1C2452] disabled:bg-slate-50"
            />
            <button
              type="submit"
              disabled={!canSend}
              aria-label="Send"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#F2A93B] text-[#1C2452] transition hover:bg-[#f5b85a] disabled:opacity-40"
            >
              <Icon name="send" className="h-4 w-4" />
            </button>
          </form>
          {draft.length > MAX_CHARS * 0.8 && (
            <p className="px-3 pb-2 text-right text-[11px] text-slate-500">
              {draft.length}/{MAX_CHARS}
            </p>
          )}
        </section>
      )}

      <button
        ref={launcher}
        onClick={() => (open ? close() : setOpen(true))}
        aria-expanded={open}
        aria-label={open ? 'Close help' : 'Open help'}
        className="fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-full bg-[#1C2452] px-4 py-3 text-sm font-medium text-white shadow-lg hover:bg-[#283372]"
      >
        <Icon name={open ? 'close' : 'chat'} className="h-5 w-5 text-[#F2A93B]" />
        {open ? 'Close' : 'Help'}
      </button>
    </>
  )
}

type PublicMessage = { id: string; sender: 'user' | 'bot'; message: string; created_at: string }

/** Help before login: each question goes to POST /chat/public with the page. */
function usePublicHelp() {
  const [messages, setMessages] = useState<PublicMessage[]>([])
  const [typing, setTyping] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  function send(text: string, page: string | null): boolean {
    const m = text.trim()
    if (!m || typing) return false
    setNotice(null)
    const now = new Date().toISOString()
    setMessages((prev) => [...prev, { id: `u-${Date.now()}`, sender: 'user', message: m, created_at: now }])
    setTyping(true)
    api
      .post<{ reply: string }>('/chat/public', { message: m, page })
      .then(({ data }) =>
        setMessages((prev) => [...prev, { id: `b-${Date.now()}`, sender: 'bot', message: data.reply, created_at: new Date().toISOString() }]),
      )
      .catch((e) => setNotice(apiErrorMessage(e, 'Help is unavailable right now. Try again in a moment.')))
      .finally(() => setTyping(false))
    return true
  }

  return { messages, typing, notice, send }
}
