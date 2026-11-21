import { useParams, Link } from 'react-router-dom'
import { TicketsCard } from '@/features/tickets/TicketsCard'
import { formatDate, formatINR, useTrip } from '@/features/trips/api'
import { useTripProgress, type ProgressStep } from '@/features/trips/useTripProgress'
import { TripMap } from '@/features/trips/TripMap'
import { ExportBar } from '@/features/trips/ExportBar'
import { PlanActions } from '@/features/trips/PlanActions'
import { TripHero } from '@/features/trips/TripHero'
import { GroupPanel } from '@/features/trips/GroupPanel'
import { FeedbackCard } from '@/features/trips/FeedbackCard'
import type { ItineraryDay, MemorySource, Thinking } from '@/features/trips/types'

export function TripDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: trip, isPending, isError } = useTrip(id)
  const live = useTripProgress(id, trip?.status === 'processing')

  if (isPending) return <p className="text-sm text-slate-500">Loading your trip…</p>
  if (isError || !trip) {
    return (
      <p className="text-sm text-slate-600">
        That trip could not be found.{' '}
        <Link to="/dashboard" className="underline">
          Back to dashboard
        </Link>
      </p>
    )
  }

  return (
    <div className="space-y-8">
      <TripHero
        trip={trip}
        exportBar={
          trip.status === 'completed' ? (
            <div className="flex flex-wrap items-center gap-3">
              <ExportBar tripId={trip.id} />
              <PlanActions trip={trip} />
            </div>
          ) : undefined
        }
      />

      {trip.status === 'processing' && <PlanningProgress steps={live.steps} />}

      {trip.status === 'failed' && (
        <p role="alert" className="rounded bg-red-50 px-4 py-3 text-sm text-red-700">
          {trip.error ?? 'This plan could not be generated.'}
        </p>
      )}

      {trip.status === 'completed' && <FeedbackCard tripId={trip.id} isOwner={trip.role === 'owner'} />}

      {trip.itinerary?.thinking && <ThinkingCard thinking={trip.itinerary.thinking} ownPlan={trip.source !== 'ai'} />}

      {trip.itinerary && trip.source !== 'ai' && trip.itinerary.explanation && (
        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-medium text-slate-700">{trip.source === 'manual' ? 'Your notes' : 'About this plan'}</h2>
          <p className="mt-1 whitespace-pre-line text-sm text-slate-600">{trip.itinerary.explanation}</p>
        </section>
      )}

      {trip.itinerary && trip.source === 'ai' && (
        <WhyThisPlan
          explanation={trip.itinerary.explanation}
          sources={trip.itinerary.memory_sources ?? []}
          usedMemory={trip.use_memory}
        />
      )}

      {trip.itinerary && (
        <>
          <BudgetBreakdown
            breakdown={trip.itinerary.budget_breakdown}
            total={Number(trip.budget)}
          />
          <TicketsCard tripId={trip.id} title="Tickets for this trip" />
          <TripMap days={trip.itinerary.day_plan} />
          <GroupPanel trip={trip} />
          <section className="space-y-4">
            <h2 className="text-lg font-medium">Day by day</h2>
            {trip.itinerary.day_plan.map((day) => (
              <DayCard key={day.day} day={day} />
            ))}
          </section>
        </>
      )}
    </div>
  )
}

const ALL_STEPS = [
  { step: 'started', label: 'Reading your request' },
  { step: 'retrieving', label: 'Looking through your past trips' },
  { step: 'thinking', label: 'Thinking it through — season, crowds, budget' },
  { step: 'generating', label: 'Planning your days' },
  { step: 'mapping', label: 'Finding places on the map' },
  { step: 'saving', label: 'Saving to your travel memory' },
]

function PlanningProgress({ steps }: { steps: ProgressStep[] }) {
  const reached = new Set(steps.map((s) => s.step))
  const current = steps.at(-1)?.step
  const thinking = [...steps].reverse().find((s) => s.step === 'thinking' && s.thoughts?.length)

  return (
    <section
      aria-live="polite"
      className="rounded-lg border border-slate-200 bg-white p-5"
    >
      <h2 className="mb-3 text-sm font-medium text-slate-700">Building your plan…</h2>
      <ol className="space-y-2 text-sm">
        {ALL_STEPS.map(({ step, label }) => {
          const done = reached.has(step) && step !== current
          const now = step === current
          return (
            <li key={step} className="flex items-center gap-3">
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full text-xs ${
                  done
                    ? 'bg-slate-900 text-white'
                    : now
                      ? 'animate-pulse border-2 border-slate-900'
                      : 'border border-slate-300'
                }`}
              >
                {done ? '✓' : ''}
              </span>
              <span className={done || now ? 'text-slate-900' : 'text-slate-400'}>{label}</span>
            </li>
          )
        })}
      </ol>
      {thinking?.thoughts && (
        <ul className="mt-4 space-y-1.5 border-t border-slate-100 pt-4 text-sm text-slate-600">
          {thinking.thoughts.map((t) => (
            <li key={t} className="flex gap-2">
              <span aria-hidden className="text-indigo-500">›</span>
              <span>{t}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

const SEASON_STYLE: Record<string, string> = {
  ideal: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  pleasant: 'bg-teal-50 text-teal-800 ring-teal-200',
  hot: 'bg-amber-50 text-amber-800 ring-amber-200',
  rainy: 'bg-sky-50 text-sky-800 ring-sky-200',
  cold: 'bg-indigo-50 text-indigo-800 ring-indigo-200',
}
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const CROWD_TEXT = { busy: 'Busy time', average: 'Normal crowds', quiet: 'Quieter time' }

/** Think on the Plan: what the planner weighed before it wrote the days. */
function ThinkingCard({ thinking, ownPlan = false }: { thinking: Thinking; ownPlan?: boolean }) {
  const chips: { text: string; cls: string }[] = []
  for (const s of thinking.seasons) {
    chips.push({
      text: `${MONTH_NAMES[s.month - 1]}: ${s.label} · ${Math.round(s.confidence * 100)}% sure`,
      cls: SEASON_STYLE[s.label] ?? 'bg-slate-50 text-slate-700 ring-slate-200',
    })
  }
  chips.push({ text: CROWD_TEXT[thinking.crowd], cls: 'bg-slate-50 text-slate-700 ring-slate-200' })
  if (thinking.budget.verdict) {
    chips.push({
      text: `Budget: ${thinking.budget.verdict} (${formatINR(thinking.budget.on_ground_per_day)}/person/day)`,
      cls: 'bg-slate-50 text-slate-700 ring-slate-200',
    })
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="text-sm font-medium text-slate-700">{ownPlan ? 'Season and weather' : 'How we thought about it'}</h2>
      <p className="mt-1 text-base font-medium text-slate-900">{thinking.headline}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {chips.map((c) => (
          <span key={c.text} className={`rounded-full px-3 py-1 text-xs font-medium ring-1 ${c.cls}`}>
            {c.text}
          </span>
        ))}
      </div>
      <ul className="mt-4 space-y-1.5 text-sm text-slate-600">
        {/* The first thought repeats the headline -- the chips already carry its confidence. */}
        {thinking.thoughts
          .filter((t) => !t.startsWith(thinking.headline))
          // On a plan the traveller wrote, drop the planner's "I'll ..." lines.
          .filter((t) => !ownPlan || !/\bI(?:'ll| will| am going to)\b/.test(t))
          .map((t) => (
          <li key={t} className="flex gap-2">
            <span aria-hidden className="text-indigo-500">›</span>
            <span>{t}</span>
          </li>
        ))}
      </ul>
      <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500">
        Season readings come from a model trained on curated climate data; costs are curated
        estimates. Crowd levels use Ministry of Tourism monthly figures.
      </p>
    </section>
  )
}

function WhyThisPlan({
  explanation,
  sources,
  usedMemory,
}: {
  explanation: string | null
  sources: MemorySource[]
  usedMemory: boolean
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="text-sm font-medium text-slate-700">Why this plan</h2>
      {explanation && <p className="mt-1 text-sm text-slate-600">{explanation}</p>}

      <div className="mt-4 border-t border-slate-100 pt-4 text-sm">
        {!usedMemory && (
          <p className="text-slate-500">Past trips were not used for this plan.</p>
        )}
        {usedMemory && sources.length === 0 && (
          <p className="text-slate-500">
            No similar past trips yet — this plan will help shape your next one.
          </p>
        )}
        {usedMemory && sources.length > 0 && (
          <>
            <p className="mb-2 font-medium text-slate-700">Shaped by your past trips</p>
            <ul className="space-y-1.5">
              {sources.map((s) => (
                <li key={s.trip_id} className="flex items-center gap-3">
                  <Link to={`/trips/${s.trip_id}`} className="flex-1 hover:underline">
                    {s.destination}
                    <span className="ml-2 text-slate-500">{formatDate(s.start_date)}</span>
                  </Link>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                    {Math.round(s.similarity * 100)}% match
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </section>
  )
}

function DayCard({ day }: { day: ItineraryDay }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white">
      <header className="flex items-baseline justify-between border-b border-slate-100 px-5 py-3">
        <h3 className="font-medium">Day {day.day}</h3>
        <span className="text-sm text-slate-500">{formatDate(day.date)}</span>
      </header>
      <ul className="divide-y divide-slate-100">
        {day.items.length === 0 && <li className="px-5 py-3 text-sm text-slate-500">Nothing planned for this day.</li>}
        {day.items.map((item, i) => (
          <li key={i} className="flex gap-4 px-5 py-3 text-sm">
            <span className="w-14 shrink-0 font-mono text-slate-500">{item.time}</span>
            <span className="flex-1">
              <span className="block font-medium">{item.activity}</span>
              <span className="text-slate-500">{item.place}</span>
            </span>
            <span className="shrink-0 text-slate-600">
              {item.estimated_cost ? formatINR(item.estimated_cost) : ''}
            </span>
          </li>
        ))}
      </ul>
    </article>
  )
}

function BudgetBreakdown({
  breakdown,
  total,
}: {
  breakdown: Record<string, number>
  total: number
}) {
  const rows = Object.entries(breakdown)
  const planned = rows.reduce((sum, [, v]) => sum + v, 0)
  const max = Math.max(...rows.map(([, v]) => v), 1)
  if (rows.length === 0) return null

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <header className="mb-4 flex items-baseline justify-between">
        <h2 className="text-lg font-medium">Budget</h2>
        <span className="text-sm text-slate-500">
          {total > 0 ? `${formatINR(planned)} of ${formatINR(total)}` : `${formatINR(planned)} planned`}
        </span>
      </header>

      <dl className="space-y-3">
        {rows.map(([label, value]) => (
          <div key={label} className="text-sm">
            <div className="mb-1 flex justify-between">
              <dt className="capitalize text-slate-700">{label}</dt>
              <dd className="text-slate-600">{formatINR(value)}</dd>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-slate-700"
                style={{ width: `${(value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </dl>
    </section>
  )
}
