/**
 * Small, dependency-free chart pieces for the Insights page.
 *
 * Built to the dataviz rules this project follows:
 *  - one series, one colour; colour comes from CSS roles (--viz-*), never hex
 *  - thin marks: bars <= 24px, 4px rounded data-end, square at the baseline
 *  - hairline solid grid; muted axis text; text never wears the data colour
 *  - labels are selective; every value is reachable by hover, by keyboard
 *    focus, and in the table view under each chart
 */
import { useRef, useState, type ReactNode } from 'react'
import type { Source } from '@/features/insights/api'

// --- tooltip ------------------------------------------------------------------

interface Tip {
  x: number
  y: number
  value: string
  label: string
}

function useTooltip() {
  const frame = useRef<HTMLDivElement>(null)
  const [tip, setTip] = useState<Tip | null>(null)

  function show(target: HTMLElement, value: string, label: string) {
    const box = frame.current?.getBoundingClientRect()
    const mark = target.getBoundingClientRect()
    if (!box) return
    // Keep the bubble's centre far enough from either edge that it never
    // hangs outside the card (it is ~200px wide at most).
    const HALF = 100
    const centre = mark.left - box.left + mark.width / 2
    const x = Math.min(Math.max(centre, HALF), Math.max(box.width - HALF, HALF))
    setTip({ x, y: mark.top - box.top, value, label })
  }

  const bubble = tip && (
    <div
      role="status"
      className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs shadow-sm"
      style={{ left: tip.x, top: tip.y - 6 }}
    >
      {/* Values lead, labels follow. */}
      <span className="block font-semibold text-[color:var(--viz-ink)]">{tip.value}</span>
      <span className="block text-[color:var(--viz-ink-2)]">{tip.label}</span>
    </div>
  )

  return { frame, show, hide: () => setTip(null), bubble }
}

// --- figures ------------------------------------------------------------------

export function StatTile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-sm text-slate-600">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
      {note && <div className="mt-1 text-xs text-slate-500">{note}</div>}
    </div>
  )
}

// --- card with a table view and sources ------------------------------------------

export function ChartCard({
  title,
  subtitle,
  sources,
  table,
  children,
}: {
  title: string
  subtitle: string
  sources: Source[]
  table: ReactNode
  children: ReactNode
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      <p className="mt-0.5 text-sm text-slate-600">{subtitle}</p>
      <div className="mt-4">{children}</div>
      <details className="mt-4 text-sm">
        <summary className="cursor-pointer text-slate-600 hover:text-slate-900">
          Show as table
        </summary>
        <div className="mt-2 overflow-x-auto">{table}</div>
      </details>
      <p className="mt-3 text-xs text-slate-500">
        Source:{' '}
        {sources.map((s, i) => (
          <span key={s.url}>
            {i > 0 && ' · '}
            <a href={s.url} target="_blank" rel="noreferrer" className="underline hover:text-slate-700">
              {s.title}
            </a>
          </span>
        ))}
      </p>
    </section>
  )
}

export function DataTable({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return (
    <table className="w-full text-left text-sm tabular-nums">
      <thead>
        <tr className="border-b border-slate-200 text-slate-600">
          {head.map((h, i) => (
            <th key={h} className={`py-1.5 font-medium ${i > 0 ? 'pl-4 text-right' : ''}`}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={String(r[0])} className="border-b border-slate-100 last:border-0">
            {r.map((c, i) => (
              <td key={i} className={`py-1.5 ${i > 0 ? 'pl-4 text-right' : ''}`}>{c}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

// --- column chart (one series over months) --------------------------------------

/** Four clean intervals that just cover `max` (10.82 -> 0, 3, 6, 9, 12). */
function niceTicks(max: number, intervals = 4): number[] {
  const raw = max / intervals
  const mag = Math.pow(10, Math.floor(Math.log10(raw)))
  const step = [1, 2, 2.5, 3, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag
  const top = Math.ceil(max / step) * step
  return Array.from({ length: Math.round(top / step) + 1 }, (_, i) => +(i * step).toFixed(6))
}

export function ColumnChart({
  data,
  color,
  format,
  unitLabel,
  labelled,
  capFormat = format,
}: {
  data: { x: string; y: number }[]
  color: string
  format: (v: number) => string
  /** Shorter format for the few values printed on the caps. */
  capFormat?: (v: number) => string
  unitLabel: string
  /** x values whose value is printed on the cap -- keep this to one or two. */
  labelled: string[]
}) {
  const { frame, show, hide, bubble } = useTooltip()
  const ticks = niceTicks(Math.max(...data.map((d) => d.y)))
  const top = ticks[ticks.length - 1]
  const PLOT = 180

  return (
    // pt-3: headroom so the top tick label and cap labels are never clipped
    <div ref={frame} className="relative pt-3">
      <div className="flex">
        {/* y axis */}
        <div className="relative w-10 shrink-0" style={{ height: PLOT }}>
          {ticks.map((t) => (
            <span
              key={t}
              className="absolute right-2 -translate-y-1/2 text-[11px] tabular-nums text-[color:var(--viz-ink-muted)]"
              style={{ bottom: `${(t / top) * 100}%` }}
            >
              {Number.isInteger(t) ? t : t.toFixed(1)}
            </span>
          ))}
        </div>

        <div className="flex-1">
          <div className="relative" style={{ height: PLOT }}>
            {ticks.map((t) => (
              <div
                key={t}
                className="absolute inset-x-0 h-px"
                style={{
                  bottom: `${(t / top) * 100}%`,
                  background: t === 0 ? 'var(--viz-axis)' : 'var(--viz-grid)',
                }}
              />
            ))}
            <div className="absolute inset-0 flex">
              {data.map((d) => (
                <div
                  key={d.x}
                  tabIndex={0}
                  aria-label={`${d.x}: ${format(d.y)}`}
                  onPointerEnter={(e) => show(e.currentTarget.lastElementChild as HTMLElement, format(d.y), `${d.x} · ${unitLabel}`)}
                  onFocus={(e) => show(e.currentTarget.lastElementChild as HTMLElement, format(d.y), `${d.x} · ${unitLabel}`)}
                  onPointerLeave={hide}
                  onBlur={hide}
                  className="group relative flex h-full flex-1 items-end justify-center outline-none"
                >
                  {labelled.includes(d.x) && (
                    <span
                      className="absolute whitespace-nowrap text-[11px] font-medium tabular-nums text-[color:var(--viz-ink-2)]"
                      style={{ bottom: `calc(${(d.y / top) * 100}% + 4px)` }}
                    >
                      {capFormat(d.y)}
                    </span>
                  )}
                  <div
                    className="w-[60%] max-w-6 rounded-t transition-opacity group-hover:opacity-75 group-focus-visible:ring-2 group-focus-visible:ring-slate-400"
                    style={{ height: `${(d.y / top) * 100}%`, background: color }}
                  />
                </div>
              ))}
            </div>
          </div>
          {/* x axis band -- part of the chart's height, never clipped */}
          <div className="mt-1.5 flex">
            {data.map((d) => (
              <span key={d.x} className="flex-1 text-center text-[11px] text-[color:var(--viz-ink-muted)]">
                <span className="hidden sm:inline">{d.x}</span>
                <span className="sm:hidden" aria-hidden="true">{d.x.slice(0, 1)}</span>
              </span>
            ))}
          </div>
        </div>
      </div>
      {bubble}
    </div>
  )
}

// --- horizontal ranked bars -----------------------------------------------------

export function BarList({
  data,
  color,
  format,
  describe,
}: {
  data: { label: string; value: number }[]
  color: string
  format: (v: number) => string
  /** Secondary tooltip line, e.g. share of the national total. */
  describe: (d: { label: string; value: number }) => string
}) {
  const { frame, show, hide, bubble } = useTooltip()
  const max = Math.max(...data.map((d) => d.value))

  return (
    <div ref={frame} className="relative">
      <ol className="space-y-1.5">
        {data.map((d) => {
          const tip = (el: HTMLElement) => show(el, format(d.value), describe(d))
          return (
            <li
              key={d.label}
              tabIndex={0}
              aria-label={`${d.label}: ${format(d.value)}`}
              onPointerEnter={(e) => tip(e.currentTarget.querySelector('[data-bar]') as HTMLElement)}
              onFocus={(e) => tip(e.currentTarget.querySelector('[data-bar]') as HTMLElement)}
              onPointerLeave={hide}
              onBlur={hide}
              className="group grid grid-cols-[8.5rem_1fr] items-center gap-3 rounded outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
            >
              <span className="truncate text-sm text-[color:var(--viz-ink-2)]">{d.label}</span>
              <span className="flex h-6 items-center border-l" style={{ borderColor: 'var(--viz-axis)' }}>
                <span
                  data-bar
                  className="h-4 rounded-r transition-opacity group-hover:opacity-75"
                  // Leave room at the tip for the value label.
                  style={{ width: `${(d.value / max) * 70}%`, background: color }}
                />
                <span className="ml-1.5 whitespace-nowrap text-xs tabular-nums text-[color:var(--viz-ink-2)]">
                  {format(d.value)}
                </span>
              </span>
            </li>
          )
        })}
      </ol>
      {bubble}
    </div>
  )
}
