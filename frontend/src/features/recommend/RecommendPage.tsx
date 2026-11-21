import { useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { apiErrorMessage, useAuth } from '@/lib/auth'
import { CityField } from '@/components/CityField'
import { Icon, type IconName } from '@/components/Icon'
import { STYLE_TAGS, type StyleTag } from '@/features/trips/types'
import { useBudgetRecommendations, type BudgetRequest, type Recommendation } from '@/features/recommend/api'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const MONTHS_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
  'September', 'October', 'November', 'December']

const STYLE: Record<StyleTag, { label: string; icon: IconName }> = {
  adventure: { label: 'Adventure', icon: 'mountain' },
  relax: { label: 'Relax', icon: 'sun' },
  culture: { label: 'Culture', icon: 'landmark' },
  food: { label: 'Food', icon: 'coffee' },
  nature: { label: 'Nature', icon: 'leaf' },
}

const SEASON: Record<string, { label: string; cls: string }> = {
  ideal: { label: 'Best time to go', cls: 'bg-emerald-50 text-emerald-800 ring-emerald-200' },
  pleasant: { label: 'Pleasant', cls: 'bg-sky-50 text-sky-800 ring-sky-200' },
  hot: { label: 'Hot', cls: 'bg-orange-50 text-orange-800 ring-orange-200' },
  rainy: { label: 'Monsoon', cls: 'bg-cyan-50 text-cyan-800 ring-cyan-200' },
  cold: { label: 'Cold', cls: 'bg-indigo-50 text-indigo-800 ring-indigo-200' },
}

const QUICK_BUDGETS = [15000, 30000, 50000, 100000]

const VERDICT: Record<string, { label: string; cls: string }> = {
  comfortable: { label: 'Well within budget', cls: 'bg-emerald-50 text-emerald-800' },
  fits: { label: 'Fits your budget', cls: 'bg-emerald-50 text-emerald-800' },
  tight: { label: 'A little tight', cls: 'bg-amber-50 text-amber-900' },
  over: { label: 'Over budget', cls: 'bg-red-50 text-red-800' },
}

const inr = (n: number) => `₹${Math.round(n).toLocaleString('en-IN')}`
const short = (n: number) => (n >= 100000 ? `₹${n / 100000}L` : `₹${n / 1000}k`)

const ymd = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

/** The first day of `month` that is today or later, as YYYY-MM-DD (local time). */
function nextStartIn(month: number | null): string {
  const now = new Date()
  if (!month || month - 1 === now.getMonth()) return ymd(now)
  const year = month - 1 < now.getMonth() ? now.getFullYear() + 1 : now.getFullYear()
  return ymd(new Date(year, month - 1, 1))
}

/**
 * "I have ₹X for N days -- where should I go?"
 *
 * The question sits on a dark ticket on the left (it stays in view while you
 * scroll the answers on wide screens); the answers are a ranked list on the
 * right. The headline repeats the question back with the real numbers.
 */
export function RecommendPage() {
  const { user } = useAuth()
  const [origin, setOrigin] = useState(user?.home_town ?? '')
  const [destination, setDestination] = useState('')
  const [originError, setOriginError] = useState<string | undefined>()
  const [budget, setBudget] = useState(30000)
  const [days, setDays] = useState(4)
  const [travelers, setTravelers] = useState(2)
  const [month, setMonth] = useState<number | null>(new Date().getMonth() + 1)
  const [tags, setTags] = useState<StyleTag[]>([])
  const [useMemory, setUseMemory] = useState(true)
  const [asked, setAsked] = useState<BudgetRequest | null>(null)
  const recommend = useBudgetRecommendations()
  const results = useRef<HTMLElement>(null)

  function toggle(tag: StyleTag) {
    setTags((t) => (t.includes(tag) ? t.filter((x) => x !== tag) : [...t, tag]))
  }

  function submit(e: FormEvent) {
    e.preventDefault()
    if (origin.split(',')[0].trim().length < 2) {
      setOriginError('Where are you starting from? We need it to work out the travel cost.')
      document.getElementById('route')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }
    setOriginError(undefined)
    const body: BudgetRequest = {
      budget, days, travelers, month, style_tags: tags, use_memory: useMemory,
      origin: origin.trim(), destination: destination.trim() || null,
    }
    setAsked(body)
    recommend.mutate(body, {
      // On narrow screens the answers sit below the form: bring them into view.
      onSuccess: () => {
        if (window.innerWidth < 1024) results.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      },
    })
  }

  const data = recommend.data
  const who = travelers === 1 ? 'you' : `${travelers} of you`
  const fromCity = origin.split(',')[0].trim()
  const toPlace = destination.split(',')[0].trim()

  return (
    <div className="space-y-8">
      <header className="max-w-4xl">
        <h1 className="font-display text-4xl leading-[1.08] tracking-tight text-balance text-[#1C2452] sm:text-5xl lg:text-[56px]">
          Where can {budget >= 1000 ? inr(budget) : 'your budget'} take {who}
          {fromCity ? ` from ${fromCity}` : ''}
          {toPlace ? ` in ${toPlace}` : ''}?
        </h1>
        <p className="mt-3 text-[17px] leading-relaxed text-slate-600">
          We match every place we know on your style, what it costs on the ground and the season you’d be there — and
          learn from the trips you’ve rated. Prefer to just ask?{' '}
          <Link to="/assistant" className="font-medium text-[#1C2452] underline decoration-[#F2A93B] decoration-2 underline-offset-4">
            Talk to the assistant
          </Link>
          .
        </p>
      </header>

      {/* ---- the route: from (needed) and to (optional) ---- */}
      <div
        id="route"
        className="grid gap-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 md:grid-cols-[1fr_auto_1fr] md:items-start"
      >
        <CityField
          label="From"
          value={origin}
          onChange={(v) => { setOrigin(v); setOriginError(undefined) }}
          hint="Where the trip starts — every place is priced from here."
          error={originError}
        />
        <span className="hidden h-12 w-12 items-center justify-center self-center rounded-full bg-[#F2A93B]/15 text-[#1C2452] md:mt-7 md:flex" aria-hidden>
          <Icon name="arrow" className="h-5 w-5" />
        </span>
        <CityField
          label="To"
          value={destination}
          onChange={setDestination}
          required={false}
          optional
          hint="A place for it and what’s near it, or a state like Kerala. Leave empty to see everywhere."
        />
      </div>

      <div className="grid items-start gap-8 lg:grid-cols-[380px_1fr]">
        {/* ---- the question ---- */}
        <form
          onSubmit={submit}
          className="space-y-6 rounded-[28px] bg-[#1C2452] p-6 text-white shadow-[0_20px_50px_-20px_rgba(28,36,82,0.55)] sm:p-7 lg:sticky lg:top-24"
        >
          <div>
            <label htmlFor="budget" className="text-sm text-white/70">Total budget</label>
            <div className="mt-1 flex items-baseline gap-1 border-b border-white/20 pb-2 focus-within:border-[#F2A93B]">
              <span className="font-display text-4xl text-white/60">₹</span>
              <input
                id="budget"
                type="text" inputMode="numeric" required aria-describedby="budget-hint"
                value={budget ? budget.toLocaleString('en-IN') : ''}
                onChange={(e) => {
                  const n = Number(e.target.value.replace(/\D/g, '').slice(0, 8))
                  setBudget(n)
                }}
                className="font-display w-full bg-transparent text-4xl text-white outline-none"
              />
            </div>
            {budget > 0 && budget < 1000 && (
              <p id="budget-hint" className="mt-2 text-xs text-[#F2A93B]">Enter at least ₹1,000.</p>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              {QUICK_BUDGETS.map((b) => (
                <button
                  key={b} type="button" onClick={() => setBudget(b)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                    budget === b ? 'bg-[#F2A93B] text-[#1C2452]' : 'bg-white/10 text-white/80 hover:bg-white/20'
                  }`}
                >
                  {short(b)}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Stepper label="Days" value={days} min={1} max={30} onChange={setDays} />
            <Stepper label="Travellers" value={travelers} min={1} max={20} onChange={setTravelers} />
          </div>

          <fieldset>
            <legend className="mb-2 text-sm text-white/70">When</legend>
            <div className="grid grid-cols-6 gap-1.5">
              {MONTHS.map((m, i) => (
                <Pill key={m} on={month === i + 1} onClick={() => setMonth(i + 1)} label={MONTHS_LONG[i]}>{m}</Pill>
              ))}
            </div>
            <button
              type="button" onClick={() => setMonth(null)}
              className={`mt-2 text-xs ${month === null ? 'text-[#F2A93B]' : 'text-white/60 hover:text-white'}`}
            >
              {month === null ? '✓ Any time of year' : 'Any time of year'}
            </button>
          </fieldset>

          <fieldset>
            <legend className="mb-2 text-sm text-white/70">What are you after?</legend>
            <div className="flex flex-wrap gap-2">
              {STYLE_TAGS.map((tag) => {
                const on = tags.includes(tag)
                return (
                  <button
                    key={tag} type="button" aria-pressed={on} onClick={() => toggle(tag)}
                    className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm transition ${
                      on ? 'bg-white font-medium text-[#1C2452]' : 'bg-white/10 text-white/85 hover:bg-white/20'
                    }`}
                  >
                    <Icon name={STYLE[tag].icon} className="h-4 w-4" />
                    {STYLE[tag].label}
                  </button>
                )
              })}
            </div>
          </fieldset>

          <label className="flex cursor-pointer items-start gap-3 rounded-2xl bg-white/5 p-3 text-sm ring-1 ring-white/10">
            <input
              type="checkbox" checked={useMemory} onChange={(e) => setUseMemory(e.target.checked)}
              className="mt-0.5 h-4 w-4 accent-[#F2A93B]"
            />
            <span>
              <span className="font-medium">Learn from my rated trips</span>
              <span className="mt-0.5 block text-white/60">
                Places like the ones you loved move up; ones you didn’t enjoy move down.
              </span>
            </span>
          </label>

          <button
            type="submit" disabled={recommend.isPending || budget < 1000}
            className="w-full rounded-2xl bg-[#F2A93B] px-4 py-3.5 text-[15px] font-semibold text-[#1C2452] transition hover:bg-[#f5b85a] disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            {recommend.isPending ? 'Finding places…' : 'Find places'}
          </button>
        </form>

        {/* ---- the answer ---- */}
        <section ref={results} aria-live="polite" className="min-w-0 scroll-mt-20 space-y-5">
          {recommend.isError && (
            <p role="alert" className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
              {apiErrorMessage(recommend.error, 'Could not get recommendations.')}
            </p>
          )}

          {!data && !recommend.isPending && <EmptyState />}

          {recommend.isPending && (
            <div className="space-y-4">
              {[0, 1, 2].map((i) => <div key={i} className="h-44 animate-pulse rounded-3xl bg-slate-200/60" />)}
            </div>
          )}

          {data && asked && !recommend.isPending && (
            <>
              <div className="grid gap-px overflow-hidden rounded-2xl border border-slate-200 bg-slate-200 sm:grid-cols-3">
                <Stat label="Per person, per day" value={inr(data.per_person_per_day)} />
                {data.origin_found ? (
                  <Stat label="Starting from" value={data.origin ?? ''} note="Fares worked out from here for each place" />
                ) : (
                  <Stat
                    label={`On the ground, after ${Math.round(data.travel_share * 100)}% for getting there`}
                    value={inr(data.on_ground_per_day)}
                    note={data.origin ? `We couldn’t place ${data.origin}, so travel is a flat share` : undefined}
                  />
                )}
                <Stat
                  label="Places that fit"
                  value={`${data.items.length} of ${data.considered}`}
                  note={[
                    data.over_budget > 0 ? `${data.over_budget} over budget` : '',
                    data.closed > 0 ? `${data.closed} closed that month` : '',
                  ].filter(Boolean).join(', ')}
                />
              </div>

              {data.destination_note && (
                <p
                  className={`flex items-start gap-2 rounded-2xl px-4 py-3 text-sm ${
                    data.destination_mode === 'not_found' ? 'bg-amber-50 text-amber-900' : 'bg-[#1C2452]/5 text-[#1C2452]'
                  }`}
                >
                  <Icon name="pin" className="mt-0.5 h-4 w-4 shrink-0" />
                  {data.destination_note}.
                </p>
              )}

              {data.taste.length > 0 && (
                <p className="flex items-start gap-2 text-sm text-slate-600">
                  <Icon name="star" className="mt-0.5 h-4 w-4 shrink-0 text-[#F2A93B]" />
                  Shaped by your ratings: {data.taste.join('; ')}.
                </p>
              )}

              {data.items.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
                  <p className="font-medium text-slate-800">Nothing fits this budget yet</p>
                  <p className="mt-1 text-sm text-slate-500">Try more money, fewer days or fewer travellers.</p>
                </div>
              ) : (
                <ol className="space-y-4">
                  {data.items.map((item, i) => (
                    <Result key={item.name} rank={i + 1} item={item} asked={asked} />
                  ))}
                </ol>
              )}
              <p className="text-xs leading-relaxed text-slate-500">{data.note}</p>
            </>
          )}
        </section>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- pieces

function Stepper({ label, value, min, max, onChange }: {
  label: string; value: number; min: number; max: number; onChange: (n: number) => void
}) {
  const btn = 'flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-lg text-white hover:bg-white/20 disabled:opacity-30'
  return (
    <div>
      <p className="text-sm text-white/70">{label}</p>
      <div className="mt-2 flex items-center justify-between rounded-2xl bg-white/5 p-1.5 ring-1 ring-white/10">
        <button type="button" className={btn} disabled={value <= min} onClick={() => onChange(value - 1)} aria-label={`Fewer ${label.toLowerCase()}`}>−</button>
        <span className="font-display text-3xl tabular-nums">{value}</span>
        <button type="button" className={btn} disabled={value >= max} onClick={() => onChange(value + 1)} aria-label={`More ${label.toLowerCase()}`}>+</button>
      </div>
    </div>
  )
}

function Pill({ on, onClick, label, children }: { on: boolean; onClick: () => void; label: string; children: ReactNode }) {
  return (
    <button
      type="button" aria-pressed={on} aria-label={label} onClick={onClick}
      className={`rounded-lg py-1.5 text-xs font-medium transition ${
        on ? 'bg-[#F2A93B] text-[#1C2452]' : 'bg-white/5 text-white/75 ring-1 ring-white/10 hover:bg-white/15'
      }`}
    >
      {children}
    </button>
  )
}

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="bg-white px-5 py-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
      {note && <p className="mt-0.5 text-xs text-slate-500">{note}</p>}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-8 py-14">
      <Icon name="compass" className="h-8 w-8 text-[#1C2452]" />
      <h2 className="font-display mt-4 text-3xl text-[#1C2452]">Your shortlist shows up here</h2>
      <p className="mt-2 max-w-md text-slate-600">
        Set the budget, days and month on the left, pick what you enjoy, and press Find places. Each place comes with
        why it fits, the season, and a button to plan it.
      </p>
    </div>
  )
}

function Result({ rank, item, asked }: { rank: number; item: Recommendation; asked: BudgetRequest }) {
  const params = new URLSearchParams({
    destination: `${item.name}, ${item.state}`,
    budget: String(asked.budget),
    travelers: String(asked.travelers),
    days: String(asked.days),
    start: nextStartIn(asked.month),
  })
  if (asked.style_tags.length) params.set('tags', asked.style_tags.join(','))
  const match = Math.round(item.score * 100)
  const s = item.season ? SEASON[item.season] : null
  const top = Object.entries(item.styles)
    .filter(([, v]) => v >= 0.7)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([k]) => k as StyleTag)

  return (
    <li className="grid gap-5 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-[56px_1fr_auto] sm:p-6">
      <span className="font-display text-4xl leading-none text-slate-300" aria-label={`Rank ${rank}`}>{rank}</span>

      <div className="min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h3 className="font-display text-3xl leading-tight text-[#1C2452]">{item.name}</h3>
          <span className="text-sm text-slate-500">{item.state}</span>
          {item.is_destination && (
            <span className="rounded-full bg-[#F2A93B] px-2.5 py-0.5 text-xs font-semibold text-[#1C2452]">Your pick</span>
          )}
          {item.visited && (
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">You’ve been here</span>
          )}
        </div>
        {item.blurb && <p className="mt-1 text-[15px] text-slate-600">{item.blurb}</p>}

        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          {s && <span className={`rounded-full px-2.5 py-1 font-medium ring-1 ${s.cls}`}>{s.label}</span>}
          {item.distance_km !== null && item.distance_km !== undefined && (
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-50 px-2.5 py-1 font-medium text-slate-700 ring-1 ring-slate-200">
              <Icon name={item.travel_mode === 'flight' ? 'plane' : item.travel_mode?.startsWith('bus') ? 'bus' : 'train'} className="h-3.5 w-3.5" />
              {item.distance_km.toLocaleString('en-IN')} km, {item.travel_mode}
              {item.travel_fare ? `, about ${inr(item.travel_fare)} return per person` : ''}
            </span>
          )}
          <span className="rounded-full bg-slate-50 px-2.5 py-1 font-medium text-slate-700 ring-1 ring-slate-200">
            About {inr(item.daily_cost)} per person per day there
          </span>
          {top.map((t) => (
            <span key={t} className="inline-flex items-center gap-1 rounded-full bg-slate-50 px-2.5 py-1 text-slate-600 ring-1 ring-slate-200">
              <Icon name={STYLE[t].icon} className="h-3.5 w-3.5" /> {STYLE[t].label}
            </span>
          ))}
        </div>

        <ul className="mt-3 space-y-1 text-sm text-slate-600">
          {item.reasons.map((r) => (
            <li key={r} className="flex gap-2">
              <Icon name="check" className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
              <span>{r}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex flex-row items-center justify-between gap-4 sm:w-40 sm:flex-col sm:items-end sm:justify-between">
        <div className="w-full max-w-[170px] space-y-3 sm:text-right">
          {item.estimate && (
            <div>
              <p className="text-xs text-slate-500">Rough total</p>
              <p className="text-2xl font-semibold tabular-nums text-slate-900">{inr(item.estimate.total)}</p>
              {item.estimate.verdict && (
                <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[11px] font-medium ${VERDICT[item.estimate.verdict].cls}`}>
                  {VERDICT[item.estimate.verdict].label}
                </span>
              )}
            </div>
          )}
          <div>
            <p className="text-xs text-slate-500">Match</p>
            <p className={`${item.estimate ? 'text-lg' : 'text-2xl'} font-semibold tabular-nums text-slate-900`}>{match}%</p>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-[#F2A93B]" style={{ width: `${match}%` }} />
            </div>
          </div>
        </div>
        <Link
          to={`/trips/new?${params.toString()}`}
          className="inline-flex shrink-0 items-center justify-center rounded-xl bg-[#1C2452] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#283372] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#F2A93B]"
        >
          Plan this trip
        </Link>
      </div>
    </li>
  )
}
