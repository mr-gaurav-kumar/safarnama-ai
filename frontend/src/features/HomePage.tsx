import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { Icon, LogoMark, type IconName } from '@/components/Icon'
import { CountUp, CursorGlow, Magnetic, Reveal, RotatingWord, SpotlightCard, Tilt } from '@/components/Motion'
import { useEffect, useState } from 'react'

interface Health {
  status: string
}

/* ------------------------------------------------------------------ */
/*  Content                                                            */
/* ------------------------------------------------------------------ */

const FEATURES: { icon: IconName; title: string; body: string }[] = [
  {
    icon: 'spark',
    title: 'Day-by-day itineraries',
    body: 'Destination, dates, budget and style in — a complete plan out, with timings and estimated costs for every stop.',
  },
  {
    icon: 'layers',
    title: 'Trip memory',
    body: 'Past trips are stored as embeddings and retrieved when you plan again, so each plan reflects how you actually travel.',
  },
  {
    icon: 'map',
    title: 'Mapped routes',
    body: 'Every stop is geocoded and plotted day by day, so you can see how the route flows before you go.',
  },
  {
    icon: 'wallet',
    title: 'Budget breakdown',
    body: 'Stay, food, transport and activities split out in rupees, with the reasoning behind each suggestion.',
  },
  {
    icon: 'users',
    title: 'Group planning',
    body: 'Invite companions, combine everyone’s preferences and discuss the plan in a shared trip room.',
  },
  {
    icon: 'train',
    title: 'Train search',
    body: 'Journey details from your trip, ready for IRCTC — onward and return, in one place.',
  },
]

const STEPS = [
  { title: 'Describe the trip', body: 'Search a destination on the map, set your dates, budget, travellers and style.' },
  { title: 'Review the plan', body: 'Watch the itinerary build live, then explore it on the map with a full cost breakdown.' },
  { title: 'Share and travel', body: 'Invite your group, export a PDF, book trains — and rate it afterwards to improve the next one.' },
]


const STATS = [
  { to: 2.95, decimals: 2, prefix: '', suffix: ' bn', label: 'Domestic tourist visits in India, 2024' },
  { to: 9.95, decimals: 2, prefix: '', suffix: ' mn', label: 'Foreign tourist arrivals, 2024' },
  { to: 35.02, decimals: 1, prefix: 'US$ ', suffix: ' bn', label: 'Tourism foreign exchange earnings, 2024' },
]

const FAQS = [
  { q: 'Is it free to use?', a: 'Yes. Create an account and plan as many trips as you like.' },
  {
    q: 'How does trip memory work?',
    a: 'Each finished plan is converted into an embedding. When you plan again, your most similar past trips are retrieved and given to the model as context. Your memory is private and never shared across accounts.',
  },
  {
    q: 'Can I plan with friends?',
    a: 'Yes. Invite people to a trip; each member adds their own preferences, and everyone can discuss the plan in the shared trip room.',
  },
  { q: 'Can I use the plan offline?', a: 'Download it as a PDF or have it emailed to you from the trip page.' },
  {
    q: 'What happens to my data?',
    a: 'Passwords are hashed, sessions use short-lived tokens, and deleting a trip also removes it from your trip memory.',
  },
]

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export function HomePage() {
  const { isAuthenticated } = useAuth()
  const primaryTo = isAuthenticated ? '/trips/new' : '/signup'
  const primaryLabel = isAuthenticated ? 'Plan a new trip' : 'Start planning'

  return (
    <div className="bg-white text-slate-900">
      {/* ---------- Hero ---------- */}
      <CursorGlow className="overflow-hidden border-b border-slate-200">
        <GridBackdrop />
        <div className="relative mx-auto grid max-w-[1440px] items-center gap-12 px-4 pt-14 sm:px-6 lg:gap-16 lg:px-10 pb-24 sm:pt-24 lg:grid-cols-[1.1fr_1fr] lg:pt-28">
          <div>
            <p className="inline-flex animate-fade-up items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600 shadow-sm">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75 motion-reduce:hidden" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
              </span>
              Now planning:{' '}
              <RotatingWord
                words={['Manali', 'Goa', 'Tawang', 'Bodh Gaya', 'Udaipur', 'Munnar', 'Leh', 'Varanasi']}
                className="font-semibold text-slate-900"
              />
            </p>
            <h1 className="font-display mt-6 animate-fade-up text-[2.75rem] leading-[1.05] tracking-tight text-slate-950 sm:text-6xl lg:text-7xl xl:text-8xl">
              Your next adventure,
              <br />
              <em className="text-indigo-700">perfectly planned.</em>
            </h1>
            <p className="mt-6 max-w-xl animate-fade-up text-lg leading-relaxed text-slate-600 [animation-delay:120ms]">
              Personalised, day-by-day itineraries shaped by your own trip history — with mapped
              routes, clear budgets, group planning and official tourism data built in.
            </p>
            <div className="mt-10 flex animate-fade-up flex-wrap items-center gap-3 [animation-delay:220ms]">
              <Magnetic>
                <Link
                  to={primaryTo}
                  className="group inline-flex items-center gap-2 rounded-lg bg-slate-950 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 hover:shadow-[0_12px_30px_-10px_rgba(79,70,229,0.6)]"
                >
                  {primaryLabel}
                  <Icon name="arrow" className="h-4 w-4 transition group-hover:translate-x-0.5" />
                </Link>
              </Magnetic>
              <a
                href="#features"
                className="rounded-lg border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-800 transition hover:border-slate-400"
              >
                How it works
              </a>
            </div>
            <p className="mt-8 text-sm text-slate-500">Free to use · No credit card · Plans in about a minute</p>
          </div>

          <ProductPreview />
        </div>
      </CursorGlow>

      <DestinationMarquee />

      <MoodExplorer to={primaryTo} />

      {/* ---------- Features ---------- */}
      <section id="features" className="scroll-mt-16 py-24 sm:py-32">
        <div className="mx-auto max-w-[1440px] px-4 sm:px-6 lg:px-10">
          <Reveal>
          <SectionHeading
            eyebrow="Features"
            title="Everything a trip needs, in one place"
            sub="From the first idea to the train home — planning, budgeting and coordinating without switching between a dozen tabs."
          />
          </Reveal>
          <div className="mt-16 grid gap-px overflow-hidden rounded-2xl border border-slate-200 bg-slate-200 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f, i) => (
              <Reveal key={f.title} delay={i * 70} className="bg-white">
              <SpotlightCard className="group h-full bg-white p-8">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-indigo-700 transition group-hover:scale-110 group-hover:border-indigo-200 group-hover:bg-indigo-50">
                  <Icon name={f.icon} />
                </div>
                <h3 className="mt-6 text-base font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{f.body}</p>
              </SpotlightCard>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- How it works ---------- */}
      <section className="border-y border-slate-200 bg-slate-50 py-24 sm:py-32">
        <div className="mx-auto max-w-[1440px] px-4 sm:px-6 lg:px-10">
          <SectionHeading eyebrow="How it works" title="Three steps from idea to itinerary" />
          <ol className="mt-16 grid gap-10 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <Reveal key={s.title} delay={i * 120}>
              <li className="list-none border-t border-slate-300 pt-6">
                <span className="font-display text-5xl text-indigo-700">0{i + 1}</span>
                <h3 className="mt-4 text-lg font-semibold">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{s.body}</p>
              </li>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>

      {/* ---------- Memory ---------- */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto grid max-w-[1440px] items-center gap-12 px-4 sm:px-6 lg:grid-cols-2 lg:gap-16 lg:px-10">
          <div>
            <p className="text-sm font-semibold text-indigo-700">Trip memory</p>
            <h2 className="font-display mt-3 text-4xl leading-tight tracking-tight sm:text-5xl">
              It gets better every time you travel.
            </h2>
            <p className="mt-6 text-lg leading-relaxed text-slate-600">
              Most planners start from zero. This one remembers — the pace you enjoy, the budget you
              keep, the kind of places you choose — and uses it to shape the next plan.
            </p>
            <ul className="mt-8 space-y-4">
              {[
                'Similar past trips are retrieved as context for new plans',
                'Your memory is private — it never crosses between users',
                'Delete a trip and it is removed from memory too',
                'Ratings on finished trips steer future suggestions',
              ].map((t) => (
                <li key={t} className="flex gap-3 text-slate-700">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-indigo-700">
                    <Icon name="check" className="h-3.5 w-3.5" />
                  </span>
                  {t}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04),0_12px_32px_-12px_rgba(15,23,42,0.18)]">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-slate-900">Recalled for: Udaipur, 4 days</p>
              <span className="text-xs text-slate-500">Example</span>
            </div>
            <div className="mt-5 space-y-3">
              {[
                { trip: 'Jaipur · 3 days', match: 92 },
                { trip: 'Jodhpur · 2 days', match: 86 },
                { trip: 'Rishikesh · 4 days', match: 64 },
              ].map((m) => (
                <div key={m.trip} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{m.trip}</span>
                    <span className="tabular-nums text-slate-500">{m.match}% similar</span>
                  </div>
                  <div className="mt-3 h-1.5 rounded-full bg-slate-100">
                    <div className="h-1.5 rounded-full bg-indigo-600" style={{ width: `${m.match}%` }} />
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-5 border-t border-slate-100 pt-4 text-sm text-slate-600">
              Preferred pace: relaxed mornings · Heritage and food · Mid-range stays
            </p>
          </div>
        </div>
      </section>

      {/* ---------- Data ---------- */}
      <section className="bg-slate-950 py-24 text-white sm:py-32">
        <div className="mx-auto max-w-[1440px] px-4 sm:px-6 lg:px-10">
          <div className="grid gap-12 lg:grid-cols-[1fr_1.4fr] lg:items-end">
            <div>
              <p className="text-sm font-semibold text-indigo-300">Grounded in official data</p>
              <h2 className="font-display mt-3 text-4xl leading-tight tracking-tight sm:text-5xl">
                Plans informed by how India actually travels.
              </h2>
              <p className="mt-6 text-slate-400">
                Ministry of Tourism statistics tell the planner how busy your destination and travel
                month usually are. Explore the full dataset, with every source cited.
              </p>
              <Link
                to="/insights"
                className="mt-8 inline-flex items-center gap-2 text-sm font-semibold text-white hover:text-indigo-300"
              >
                Explore tourism insights <Icon name="arrow" className="h-4 w-4" />
              </Link>
            </div>
            <dl className="grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 sm:grid-cols-3">
              {STATS.map((s) => (
                <SpotlightCard key={s.label} dark className="bg-slate-950 p-6">
                  <dt className="text-sm leading-snug text-slate-400">{s.label}</dt>
                  <dd className="font-display mt-4 text-4xl tracking-tight">
                    <CountUp to={s.to} decimals={s.decimals} prefix={s.prefix} suffix={s.suffix} />
                  </dd>
                </SpotlightCard>
              ))}
            </dl>
          </div>
          <p className="mt-6 text-xs text-slate-500">Source: India Tourism Data Compendium 2025, Ministry of Tourism.</p>
        </div>
      </section>

      {/* ---------- FAQ ---------- */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto grid max-w-[1440px] gap-12 px-4 sm:px-6 lg:grid-cols-[1fr_2fr] lg:px-10">
          <div>
            <p className="text-sm font-semibold text-indigo-700">FAQ</p>
            <h2 className="font-display mt-3 text-4xl tracking-tight">Questions, answered.</h2>
          </div>
          <div className="divide-y divide-slate-200 border-y border-slate-200">
            {FAQS.map((f) => (
              <details key={f.q} className="group py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-6 text-base font-medium">
                  {f.q}
                  <Icon name="chevron" className="h-5 w-5 shrink-0 text-slate-400 transition group-open:rotate-180" />
                </summary>
                <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600">{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- CTA ---------- */}
      <section className="px-4 pb-24 sm:px-6 lg:px-10">
        <div className="relative mx-auto max-w-[1440px] overflow-hidden rounded-3xl bg-indigo-700 px-6 py-14 sm:px-8 sm:py-16 text-center text-white sm:py-20">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_30%_0%,rgba(255,255,255,0.18),transparent_55%)]" />
          <h2 className="font-display relative text-4xl tracking-tight sm:text-5xl">Your next trip is one form away.</h2>
          <p className="relative mx-auto mt-4 max-w-xl text-indigo-100">
            Tell us where you want to go. We’ll handle the plan, the map and the budget.
          </p>
          <Link
            to={primaryTo}
            className="relative mt-10 inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-indigo-800 transition hover:bg-indigo-50"
          >
            {primaryLabel}
            <Icon name="arrow" className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Pieces                                                             */
/* ------------------------------------------------------------------ */

function GridBackdrop() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_at_top,black_30%,transparent_75%)]"
      style={{
        backgroundImage:
          'linear-gradient(to right, rgb(226 232 240) 1px, transparent 1px), linear-gradient(to bottom, rgb(226 232 240) 1px, transparent 1px)',
        backgroundSize: '48px 48px',
      }}
    />
  )
}

const PREVIEWS = [
  {
    place: 'Jaipur, Rajasthan', dates: '12–14 Dec · 2 travellers', used: 15700, budget: 25000,
    days: [
      [
        { time: '09:00', place: 'City Palace', note: 'Royal museum and courtyards', cost: '₹1,400' },
        { time: '13:00', place: 'Lunch, MI Road', note: 'Rajasthani thali', cost: '₹900' },
        { time: '17:00', place: 'Hawa Mahal', note: 'Best light in late afternoon', cost: '₹400' },
      ],
      [
        { time: '08:30', place: 'Amber Fort', note: 'Arrive early to avoid queues', cost: '₹1,000' },
        { time: '12:30', place: 'Panna Meena ka Kund', note: 'Stepwell photo stop', cost: 'Free' },
        { time: '18:30', place: 'Nahargarh Fort', note: 'Sunset over the old city', cost: '₹600' },
      ],
      [
        { time: '10:00', place: 'Johari Bazaar', note: 'Block prints and jewellery', cost: '₹2,000' },
        { time: '13:30', place: 'Lunch at LMB', note: 'Ghewar for dessert', cost: '₹800' },
        { time: '17:45', place: 'Train to Delhi', note: 'Shatabdi from Jaipur Jn', cost: '₹1,200' },
      ],
    ],
  },
  {
    place: 'Manali, Himachal Pradesh', dates: '18–21 Jan · 3 travellers', used: 21400, budget: 30000,
    days: [
      [
        { time: '09:30', place: 'Hadimba Devi Temple', note: 'Cedar forest walk', cost: 'Free' },
        { time: '13:00', place: 'Old Manali cafés', note: 'Trout and a view', cost: '₹1,200' },
        { time: '17:00', place: 'Mall Road', note: 'Woollens and local snacks', cost: '₹1,500' },
      ],
      [
        { time: '08:00', place: 'Solang Valley', note: 'Snow play and ropeway', cost: '₹2,400' },
        { time: '13:00', place: 'Lunch at Solang', note: 'Maggi point, of course', cost: '₹500' },
        { time: '16:30', place: 'Vashisht hot springs', note: 'Warm up after the snow', cost: 'Free' },
      ],
      [
        { time: '08:30', place: 'Atal Tunnel to Sissu', note: 'Lahaul valley viewpoints', cost: '₹3,500' },
        { time: '14:00', place: 'Sissu waterfall', note: 'Frozen in peak winter', cost: 'Free' },
        { time: '18:00', place: 'Back in Manali', note: 'Bonfire dinner', cost: '₹1,800' },
      ],
    ],
  },
  {
    place: 'North Goa', dates: '6–8 Feb · 2 travellers', used: 12900, budget: 20000,
    days: [
      [
        { time: '10:00', place: 'Fort Aguada', note: 'Lighthouse and sea views', cost: '₹100' },
        { time: '13:00', place: 'Candolim beach shack', note: 'Fish thali and kokum', cost: '₹900' },
        { time: '18:00', place: 'Sunset at Sinquerim', note: 'Golden hour', cost: 'Free' },
      ],
      [
        { time: '09:30', place: 'Basilica of Bom Jesus', note: 'Old Goa, UNESCO site', cost: 'Free' },
        { time: '12:30', place: 'Fontainhas walk', note: 'Latin quarter of Panaji', cost: 'Free' },
        { time: '18:30', place: 'Mandovi river cruise', note: 'Music on board', cost: '₹600' },
      ],
      [
        { time: '10:00', place: 'Anjuna flea market', note: 'Wednesdays only', cost: '₹1,500' },
        { time: '15:00', place: 'Chapora Fort', note: 'Short climb, big view', cost: 'Free' },
        { time: '19:30', place: 'Dinner in Assagao', note: 'Goan-Portuguese menu', cost: '₹2,200' },
      ],
    ],
  },
]

const INR_FMT = new Intl.NumberFormat('en-IN')

/** The hero's live-looking itinerary: it flips through days and trips on its
 *  own, and pauses while the pointer is over it. */
function ProductPreview() {
  // One counter walks every day of every example: step 0-2 is trip 1, 3-5 trip 2...
  const [step, setStep] = useState(0)
  const [paused, setPaused] = useState(false)
  const trip = Math.floor(step / 3) % PREVIEWS.length
  const day = step % 3

  useEffect(() => {
    if (paused || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    const id = setInterval(() => setStep((n) => (n + 1) % (PREVIEWS.length * 3)), 3200)
    return () => clearInterval(id)
  }, [paused])

  const p = PREVIEWS[trip]
  const pct = Math.round((p.used / p.budget) * 100)

  return (
    <div className="relative animate-fade-up [animation-delay:250ms]" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
      <div className="absolute -inset-4 rounded-3xl bg-gradient-to-tr from-indigo-100 via-white to-sky-100 blur-2xl" />
      <Tilt>
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04),0_24px_48px_-16px_rgba(15,23,42,0.25)]">
        {/* window bar */}
        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-4 py-3">
          <div className="flex gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
            <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
            <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
          </div>
          <div className="flex gap-1">
            {PREVIEWS.map((_, i) => (
              <button
                key={i}
                aria-label={`Show example ${i + 1}`}
                onClick={() => setStep(i * 3)}
                className={`h-1.5 rounded-full transition-all ${i === trip ? 'w-5 bg-slate-900' : 'w-1.5 bg-slate-300'}`}
              />
            ))}
          </div>
        </div>
        <div className="p-6">
          <div key={trip} className="flex animate-fade-up items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">Itinerary</p>
              <p className="mt-1 text-xl font-semibold">{p.place}</p>
              <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-500">
                <Icon name="calendar" className="h-4 w-4" /> {p.dates}
              </p>
            </div>
            <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">
              Ready
            </span>
          </div>

          <div className="mt-6 flex gap-2 text-xs">
            {['Day 1', 'Day 2', 'Day 3'].map((d, i) => (
              <button
                key={d}
                onClick={() => setStep(trip * 3 + i)}
                className={`rounded-md px-3 py-1.5 font-medium transition ${i === day ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              >
                {d}
              </button>
            ))}
          </div>

          <ol key={`${trip}-${day}`} className="relative mt-5 min-h-[168px] space-y-4 border-l border-slate-200 pl-5">
            {p.days[day].map((s, i) => (
              <li key={s.time} className="relative animate-fade-up" style={{ animationDelay: `${i * 90}ms` }}>
                <span className="absolute top-1.5 -left-[25px] h-2.5 w-2.5 rounded-full border-2 border-white bg-indigo-600 ring-1 ring-indigo-200" />
                <div className="flex items-baseline justify-between gap-3">
                  <p className="text-sm">
                    <span className="mr-2 tabular-nums text-slate-400">{s.time}</span>
                    <span className="font-medium">{s.place}</span>
                  </p>
                  <span className="text-xs tabular-nums text-slate-500">{s.cost}</span>
                </div>
                <p className="mt-0.5 text-xs text-slate-500">{s.note}</p>
              </li>
            ))}
          </ol>

          <div className="mt-6 rounded-xl bg-slate-50 p-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Trip budget used</span>
              <span className="font-semibold tabular-nums">₹{INR_FMT.format(p.used)} of ₹{INR_FMT.format(p.budget)}</span>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200">
              <div key={trip} className="h-1.5 animate-grow-x rounded-full bg-indigo-600" style={{ width: `${pct}%` }} />
            </div>
          </div>
        </div>
      </div>
      </Tilt>
    </div>
  )
}

const MARQUEE = [
  'Manali', 'Goa', 'Tawang', 'Bodh Gaya', 'Jaipur', 'Udaipur', 'Jaisalmer', 'Leh', 'Rishikesh', 'Varanasi',
  'Munnar', 'Alleppey', 'Darjeeling', 'Gangtok', 'Hampi', 'Coorg', 'Ooty', 'Shillong', 'Andaman', 'Amritsar',
]

function DestinationMarquee() {
  const row = [...MARQUEE, ...MARQUEE]
  return (
    <div className="overflow-hidden border-b border-slate-200 bg-white py-5 [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]">
      <div className="flex w-max animate-marquee gap-10 hover:[animation-play-state:paused]">
        {row.map((d, i) => (
          <span key={i} className="font-display flex items-center gap-10 text-2xl whitespace-nowrap text-slate-400">
            {d}
            <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />
          </span>
        ))}
      </div>
    </div>
  )
}

/** Wikimedia Commons photo, resized on their side. Credits are shown under the section. */
const commons = (file: string, w = 1200) =>
  `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(file.replace(/ /g, '_'))}?width=${w}`

const MOODS: { icon: IconName; title: string; line: string; places: string[]; photo: string; credit: string }[] = [
  {
    icon: 'mountain', title: 'Mountains', line: 'Snow, pine air and slow mornings', places: ['Manali', 'Leh', 'Tawang', 'Auli'],
    photo: 'Snow Rohtang Range Manali May24 A7CR 00128.jpg', credit: 'Timothy A. Gonsalves, CC BY-SA 4.0',
  },
  {
    icon: 'sun', title: 'Beaches', line: 'Sunsets, shacks and seafood', places: ['Goa', 'Varkala', 'Havelock', 'Gokarna'],
    photo: 'Anjuna Beach, Goa, India, Legendary Curlies beach shack.jpg', credit: 'Vyacheslav Argenberg, CC BY 4.0',
  },
  {
    icon: 'landmark', title: 'Heritage', line: 'Forts, palaces and old cities', places: ['Jaipur', 'Udaipur', 'Hampi', 'Jaisalmer'],
    photo: 'Amber Fort, Jaipur, 20191219 1011 9509.jpg', credit: 'Jakub Hałun, CC BY-SA 4.0',
  },
  {
    icon: 'star', title: 'Spiritual', line: 'Temples, ghats and quiet', places: ['Varanasi', 'Rishikesh', 'Bodh Gaya', 'Amritsar'],
    photo: 'Varanasi 2010 ghats1.jpg', credit: 'Marcin Białek, CC BY-SA 3.0',
  },
  {
    icon: 'leaf', title: 'Nature', line: 'Tea hills, backwaters, wildlife', places: ['Munnar', 'Alleppey', 'Coorg', 'Kaziranga'],
    photo: 'Munnar - Tea Plantations.jpg', credit: 'Ingo Mehling, CC BY-SA 4.0',
  },
  {
    icon: 'coffee', title: 'Food trails', line: 'Street food to thali tables', places: ['Delhi', 'Lucknow', 'Kolkata', 'Hyderabad'],
    photo: 'Darjeeling, India, Indian Thali meal.jpg', credit: 'Vyacheslav Argenberg, CC BY 4.0',
  },
]

/** "What kind of trip are you craving?" -- six photo cards that come alive under the cursor. */
function MoodExplorer({ to }: { to: string }) {
  return (
    <section className="py-24 sm:py-32">
      <div className="mx-auto max-w-[1440px] px-4 sm:px-6 lg:px-10">
        <Reveal>
          <SectionHeading
            eyebrow="Plan by mood"
            title="What kind of trip are you craving?"
            sub="Pick a feeling — the planner turns it into days, routes and a budget that fits."
          />
        </Reveal>
        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {MOODS.map((m, i) => (
            <Reveal key={m.title} delay={i * 70}>
              <Link to={to} className="block rounded-3xl">
                <SpotlightCard
                  dark
                  className="group relative h-[22rem] rounded-3xl bg-slate-900 text-white shadow-[0_24px_48px_-24px_rgba(15,23,42,0.55)] transition-transform duration-500 hover:-translate-y-1.5"
                >
                  <img
                    src={commons(m.photo)}
                    alt={`${m.title} — ${m.places[0]}`}
                    loading="lazy"
                    className="absolute inset-0 h-full w-full object-cover transition duration-700 ease-out group-hover:scale-110"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-black/5 transition duration-500 group-hover:from-black/90 group-hover:via-black/40" />
                  <div className="relative flex h-[22rem] flex-col justify-between p-7">
                    <div className="flex items-start justify-between">
                      <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15 ring-1 ring-white/25 backdrop-blur transition duration-300 group-hover:rotate-[-6deg] group-hover:scale-110 group-hover:bg-white group-hover:text-slate-950">
                        <Icon name={m.icon} className="h-5 w-5" />
                      </span>
                      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 opacity-0 ring-1 ring-white/25 transition duration-300 group-hover:opacity-100">
                        <Icon name="arrow" className="h-4 w-4" />
                      </span>
                    </div>
                    <div>
                      <h3 className="font-display text-4xl tracking-tight">{m.title}</h3>
                      <p className="mt-1 text-sm text-white/80">{m.line}</p>
                      <div className="mt-4 flex max-h-0 flex-wrap gap-1.5 overflow-hidden opacity-0 transition-all duration-500 group-hover:max-h-20 group-hover:opacity-100 max-sm:max-h-20 max-sm:opacity-100">
                        {m.places.map((p) => (
                          <span key={p} className="rounded-full bg-white/15 px-2.5 py-0.5 text-xs ring-1 ring-white/25 backdrop-blur">
                            {p}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </SpotlightCard>
              </Link>
            </Reveal>
          ))}
        </div>
        <p className="mt-6 text-xs text-slate-400">
          Photos via Wikimedia Commons: {MOODS.map((m) => `${m.title} — ${m.credit}`).join(' · ')}.
        </p>
      </div>
    </section>
  )
}

function SectionHeading({ eyebrow, title, sub }: { eyebrow: string; title: string; sub?: string }) {
  return (
    <div className="max-w-2xl">
      <p className="text-sm font-semibold text-indigo-700">{eyebrow}</p>
      <h2 className="font-display mt-3 text-4xl leading-tight tracking-tight sm:text-5xl">{title}</h2>
      {sub && <p className="mt-5 text-lg leading-relaxed text-slate-600">{sub}</p>}
    </div>
  )
}

function Footer() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['health'],
    queryFn: async () => (await api.get<Health>('/health')).data,
  })

  return (
    <footer className="border-t border-slate-200">
      <div className="mx-auto grid max-w-[1440px] gap-10 px-4 py-14 sm:grid-cols-[2fr_1fr_1fr] sm:px-6 lg:px-10">
        <div>
          <div className="flex items-center gap-2.5 font-semibold">
            <LogoMark className="h-9 w-auto" /> Safarnama
          </div>
          <p className="mt-3 max-w-xs text-sm text-slate-500">
            Your Next Adventure, Perfectly Planned.
          </p>
        </div>
        <div>
          <p className="text-sm font-semibold">Product</p>
          <ul className="mt-4 space-y-2.5 text-sm text-slate-500">
            <li><Link to="/trips/new" className="hover:text-slate-900">Plan a trip</Link></li>
            <li><Link to="/dashboard" className="hover:text-slate-900">My trips</Link></li>
            <li><Link to="/book/trains" className="hover:text-slate-900">Train search</Link></li>
            <li><Link to="/insights" className="hover:text-slate-900">Tourism insights</Link></li>
          </ul>
        </div>
        <div>
          <p className="text-sm font-semibold">Account</p>
          <ul className="mt-4 space-y-2.5 text-sm text-slate-500">
            <li><Link to="/login" className="hover:text-slate-900">Log in</Link></li>
            <li><Link to="/signup" className="hover:text-slate-900">Sign up</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-slate-200">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-2 px-4 py-5 sm:px-6 lg:px-10 text-xs text-slate-500">
          <span>© {new Date().getFullYear()} Safarnama</span>
          <span className="flex items-center gap-1.5">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                data ? 'bg-emerald-500' : isError ? 'bg-red-500' : 'bg-slate-300'
              }`}
            />
            {isPending ? 'Checking status' : isError ? 'Service unavailable' : 'All systems operational'}
          </span>
        </div>
      </div>
    </footer>
  )
}
