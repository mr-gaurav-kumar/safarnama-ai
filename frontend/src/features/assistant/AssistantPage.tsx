import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { apiErrorMessage, useAuth } from '@/lib/auth'
import { loadChat, saveChat } from '@/lib/savedChat'
import { Icon, type IconName } from '@/components/Icon'

// ---------------------------------------------------------------- API types

interface Estimate {
  travel_mode: string | null
  travel: number | null
  stay: number
  food: number
  local: number
  total: number
  per_person: number
  verdict: 'comfortable' | 'fits' | 'tight' | 'over' | null
  distance_km: number | null
  start_date: string | null
  end_date: string | null
  nights: number
  weekend_nights: number
}
interface Pick {
  name: string
  state: string
  blurb: string
  reasons: string[]
  season: { label: 'ideal' | 'pleasant' | 'hot' | 'rainy' | 'cold'; text: string; confidence: number }
  live: { high: number; low: number; rain_chance: number; rainy_days: number; days: number } | null
  estimate: Estimate
  altitude_m: number
  coastal: boolean
  plan: Record<string, string | number>
}
interface Understood {
  budget: number | null
  days: number
  travelers: number
  month_name: string
  origin: string | null
  moods: string[]
  assumed: string[]
  when: 'weekend' | 'long_weekend' | 'weekdays' | null
}
interface Reply {
  reply: string
  intent: 'recommend' | 'place' | 'unknown' | 'help'
  understood: Understood
  picks: Pick[]
  from_model: boolean
}
type Turn = { role: 'user'; text: string } | { role: 'assistant'; text: string; data: Reply }

// ---------------------------------------------------------------- look

const INK = '#1C2452'
const MARIGOLD = '#F2A93B'
const SEASON: Record<Pick['season']['label'], { label: string; cls: string }> = {
  ideal: { label: 'Best time to go', cls: 'bg-emerald-50 text-emerald-800 ring-emerald-200' },
  pleasant: { label: 'Pleasant', cls: 'bg-sky-50 text-sky-800 ring-sky-200' },
  hot: { label: 'Hot', cls: 'bg-orange-50 text-orange-800 ring-orange-200' },
  rainy: { label: 'Monsoon', cls: 'bg-cyan-50 text-cyan-800 ring-cyan-200' },
  cold: { label: 'Cold', cls: 'bg-indigo-50 text-indigo-800 ring-indigo-200' },
}
const VERDICT: Record<string, { label: string; cls: string }> = {
  comfortable: { label: 'Well within budget', cls: 'bg-emerald-50 text-emerald-800' },
  fits: { label: 'Fits your budget', cls: 'bg-emerald-50 text-emerald-800' },
  tight: { label: 'A little tight', cls: 'bg-amber-50 text-amber-900' },
  over: { label: 'Over budget', cls: 'bg-red-50 text-red-800' },
}
// Budget parts: four fixed colours, the same in the bar and the legend.
const PARTS = [
  { key: 'travel', label: 'Getting there', color: INK },
  { key: 'stay', label: 'Stay', color: MARIGOLD },
  { key: 'food', label: 'Food', color: '#2F9C8F' },
  { key: 'local', label: 'Local travel & sights', color: '#A3ADC2' },
] as const

const EXAMPLES = [
  'Mera budget ₹20,000 hai, 3 din, Delhi se pahad mein jaana hai, 2 log',
  'Beach trip for a couple in January under ₹50,000 from Mumbai',
  'Manali January mein kaisa rahega? 4 din ka kitna kharcha?',
  'Weekend getaway, something peaceful, next month',
]

const money = (n: number) => `₹${Math.round(n).toLocaleString('en-IN')}`
const shortDay = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })
const WHEN: Record<string, string> = { weekend: 'Weekend', long_weekend: 'Long weekend', weekdays: 'Weekdays' }

/**
 * The travel assistant. Ask in English or Hinglish -- budget, days, people,
 * month, mood, where from -- and get places that fit, each with a rough
 * budget and the weather. The numbers come from the app's own models and
 * data; the language model (when connected) only writes the reply.
 */
export function AssistantPage() {
  const { user } = useAuth()
  // Kept while you move around the app or reload; cleared when you log out.
  const [turns, setTurns] = useState<Turn[]>(() => loadChat<Turn>('assistant', user?.id))
  useEffect(() => saveChat('assistant', user?.id, turns), [turns, user?.id])
  const [text, setText] = useState('')
  const end = useRef<HTMLDivElement>(null)

  const ask = useMutation({
    mutationFn: async (message: string) =>
      (await api.post<Reply>('/assistant/chat', {
        message,
        history: turns.slice(-10).map((t) => ({ role: t.role, text: t.text })),
      })).data,
    onSuccess: (data) => setTurns((t) => [...t, { role: 'assistant', text: data.reply, data }]),
  })

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [turns, ask.isPending])

  function send(message: string) {
    const m = message.trim()
    if (!m || ask.isPending) return
    setTurns((t) => [...t, { role: 'user', text: m }])
    setText('')
    ask.mutate(m)
  }

  function submit(e: FormEvent) {
    e.preventDefault()
    send(text)
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col">
      <header className="mb-8">
        <h1 className="font-display text-5xl tracking-tight text-[#1C2452] sm:text-6xl">Where to next{user?.name ? `, ${user.name.split(' ')[0]}` : ''}?</h1>
        <p className="mt-3 max-w-2xl text-[17px] leading-relaxed text-slate-600">
          Tell me your budget, how many days, who’s coming and the mood you’re in. I’ll suggest places with a rough
          budget and what the weather will be like. Hindi, English or Hinglish — all fine.
        </p>
      </header>

      {turns.length > 0 && (
        <div className="-mt-4 mb-6 flex justify-end">
          <button
            type="button"
            onClick={() => setTurns([])}
            disabled={ask.isPending}
            className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 disabled:opacity-50"
          >
            New chat
          </button>
        </div>
      )}

      {turns.length === 0 && (
        <section aria-label="Try asking" className="mb-8 grid gap-3 sm:grid-cols-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => send(ex)}
              className="rounded-2xl border border-slate-200 bg-white px-5 py-4 text-left text-[15px] leading-snug text-slate-700 shadow-sm transition hover:border-[#1C2452]/40 hover:text-slate-950 focus-visible:outline-2 focus-visible:outline-[#1C2452]"
            >
              “{ex}”
            </button>
          ))}
        </section>
      )}

      <div className="space-y-8 pb-6">
        {turns.map((t, i) =>
          t.role === 'user' ? (
            <div key={i} className="flex justify-end">
              <p className="max-w-[80%] rounded-2xl rounded-br-md bg-[#1C2452] px-5 py-3 text-[15px] text-white">{t.text}</p>
            </div>
          ) : (
            <AssistantTurn key={i} data={t.data} />
          ),
        )}
        {ask.isPending && (
          <div className="flex items-center gap-3 text-sm text-slate-500">
            <Avatar />
            Checking places, prices and the weather…
          </div>
        )}
        {ask.isError && (
          <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
            {apiErrorMessage(ask.error, 'The assistant could not answer that. Try again in a moment.')}
          </p>
        )}
        <div ref={end} />
      </div>

      <form
        onSubmit={submit}
        className="sticky bottom-4 mt-2 flex items-end gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-[0_10px_30px_-12px_rgba(28,36,82,0.35)]"
      >
        <label htmlFor="ask" className="sr-only">Ask the travel assistant</label>
        <textarea
          id="ask"
          rows={1}
          value={text}
          maxLength={500}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send(text)
            }
          }}
          placeholder="e.g. ₹15,000 mein 3 din, Delhi se, kuch peaceful"
          className="max-h-40 min-h-[48px] flex-1 resize-none bg-transparent px-3 py-3 text-[15px] outline-none placeholder:text-slate-400"
        />
        <button
          type="submit"
          disabled={!text.trim() || ask.isPending}
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#F2A93B] text-[#1C2452] transition hover:bg-[#f5b85a] disabled:opacity-40"
          aria-label="Send"
        >
          <Icon name="send" className="h-5 w-5" />
        </button>
      </form>
      <p className="mt-2 text-center text-xs text-slate-400">
        Budgets are rough estimates — the likely fare to get there plus typical local costs. Check real prices before you book.
      </p>
    </div>
  )
}

// ---------------------------------------------------------------- a reply

function Avatar() {
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#1C2452] text-[#F2A93B]">
      <Icon name="compass" className="h-5 w-5" />
    </span>
  )
}

function AssistantTurn({ data }: { data: Reply }) {
  const u = data.understood
  const chips: { icon: IconName; text: string }[] = []
  if (data.intent !== 'help' && data.intent !== 'unknown') {
    if (u.budget) chips.push({ icon: 'wallet', text: money(u.budget) })
    chips.push({ icon: 'calendar', text: `${u.days} ${u.days === 1 ? 'day' : 'days'} in ${u.month_name}` })
    chips.push({ icon: 'users', text: `${u.travelers} ${u.travelers === 1 ? 'traveller' : 'travellers'}` })
    if (u.when) chips.push({ icon: 'calendar', text: WHEN[u.when] })
    if (u.origin) chips.push({ icon: 'pin', text: `From ${u.origin}` })
    u.moods.forEach((m) => chips.push({ icon: 'compass', text: m[0].toUpperCase() + m.slice(1) }))
  }

  return (
    <div className="flex gap-3">
      <Avatar />
      <div className="min-w-0 flex-1 space-y-4">
        <p className="whitespace-pre-line text-[16px] leading-relaxed text-slate-800">{data.reply}</p>
        <p className="text-xs text-slate-400">
          {data.from_model ? 'Written by Gemini from our trip data' : 'Quick answer from our trip data (AI not connected)'}
        </p>
        {chips.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {chips.map((c) => (
              <span key={c.text} className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700">
                <Icon name={c.icon} className="h-3.5 w-3.5 text-slate-500" /> {c.text}
              </span>
            ))}
            {u.assumed.length > 0 && (
              <span className="rounded-full px-3 py-1 text-xs text-slate-500">
                Assumed {u.assumed.join(', ')} — tell me if that’s wrong
              </span>
            )}
          </div>
        )}
        {data.picks.length > 0 && (
          <div className={`grid gap-4 ${data.picks.length > 1 ? 'md:grid-cols-2' : ''}`}>
            {data.picks.map((p) => <PickCard key={p.name} p={p} />)}
          </div>
        )}
      </div>
    </div>
  )
}

function PickCard({ p }: { p: Pick }) {
  const e = p.estimate
  const s = SEASON[p.season.label]
  const v = e.verdict ? VERDICT[e.verdict] : null
  const parts = PARTS.filter((x) => (e[x.key] ?? 0) > 0)
  const plan = new URLSearchParams(Object.entries(p.plan).map(([k, val]) => [k, String(val)]))

  return (
    <article className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-3xl leading-tight text-[#1C2452]">{p.name}</h3>
          <p className="text-sm text-slate-500">
            {p.state}
            {e.distance_km ? `, about ${e.distance_km.toLocaleString('en-IN')} km away` : ''}
          </p>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${s.cls}`}>{s.label}</span>
      </div>

      {/* weather */}
      <div className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-sm">
        <p className="flex items-center gap-2 text-slate-800">
          <Icon name="sun" className="h-4 w-4 text-slate-500" />
          <span>Usually {p.season.text}</span>
        </p>
        {p.live && (
          <p className="mt-1.5 pl-6 text-slate-600">
            Next {p.live.days} days: {p.live.low}° to {p.live.high}°C
            {p.live.rain_chance >= 30 ? `, up to ${p.live.rain_chance}% chance of rain` : ', mostly dry'}
          </p>
        )}
      </div>

      {/* dates: weekend nights cost more, weekdays are quieter */}
      {e.start_date && e.end_date && (
        <p className="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate-700">
          <Icon name="calendar" className="h-4 w-4 text-slate-500" />
          {shortDay(e.start_date)}
          {e.end_date !== e.start_date && <> to {shortDay(e.end_date)}</>}
          {e.weekend_nights > 0 ? (
            <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-900">
              {e.weekend_nights} weekend {e.weekend_nights === 1 ? 'night' : 'nights'}, stays ~25% higher
            </span>
          ) : (
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-800">
              Weekday stay, cheaper and quieter
            </span>
          )}
        </p>
      )}

      {/* budget */}
      <div className="mt-4">
        <div className="flex items-end justify-between gap-2">
          <div>
            <p className="text-xs text-slate-500">Rough total</p>
            <p className="text-2xl font-semibold tabular-nums text-slate-900">{money(e.total)}</p>
          </div>
          {v && <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${v.cls}`}>{v.label}</span>}
        </div>
        <div className="mt-3 flex h-2.5 gap-0.5 overflow-hidden rounded-full" role="img" aria-label="Budget split">
          {parts.map((x) => (
            <span key={x.key} style={{ width: `${((e[x.key] ?? 0) / e.total) * 100}%`, background: x.color }} />
          ))}
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
          {parts.map((x) => (
            <div key={x.key} className="flex items-center justify-between gap-2">
              <dt className="flex items-center gap-1.5 text-slate-600">
                <span className="h-2 w-2 rounded-full" style={{ background: x.color }} />
                {x.label}
              </dt>
              <dd className="tabular-nums text-slate-900">{money(e[x.key] ?? 0)}</dd>
            </div>
          ))}
        </dl>
        {e.travel_mode && (
          <p className="mt-2 text-xs text-slate-500">
            Getting there by {e.travel_mode}, return fare for everyone included.
          </p>
        )}
        {e.travel === null && (
          <p className="mt-2 text-xs text-slate-500">Tell me where you’re starting from to add the travel cost.</p>
        )}
      </div>

      {p.reasons.length > 0 && (
        <ul className="mt-4 space-y-1 text-sm text-slate-600">
          {p.reasons.slice(0, 2).map((r) => (
            <li key={r} className="flex gap-2">
              <Icon name="check" className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
              <span>{r}</span>
            </li>
          ))}
        </ul>
      )}

      <Link
        to={`/trips/new?${plan.toString()}`}
        className="mt-5 inline-flex items-center justify-center gap-2 rounded-xl bg-[#1C2452] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#283372] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#F2A93B]"
      >
        Plan this trip
      </Link>
    </article>
  )
}
