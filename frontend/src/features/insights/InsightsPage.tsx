import { useState } from 'react'
import { useInsights, type Report, type Source } from '@/features/insights/api'
import { BarList, ChartCard, ColumnChart, DataTable, StatTile } from '@/features/insights/charts'

const MONTH_NAMES: Record<string, string> = {
  Jan: 'January', Feb: 'February', Mar: 'March', Apr: 'April', May: 'May', Jun: 'June',
  Jul: 'July', Aug: 'August', Sep: 'September', Oct: 'October', Nov: 'November', Dec: 'December',
}

/** Up to three decimals, trailing zeros dropped -- the precision the source used. */
const asPublished = (v: number) => v.toLocaleString('en-IN', { maximumFractionDigits: 3 })
const lakh = (v: number) => `${v.toFixed(2)} lakh`
const million = (v: number) => `${v.toLocaleString('en-IN', { maximumFractionDigits: 2 })} million`
const usd = (v: number) => `US$ ${v.toFixed(2)} bn`
const pct = (v: number) => `${v.toFixed(1)}%`
const count = (v: number) => v.toLocaleString('en-IN')

const SECTIONS = [
  { id: 'overview', label: 'Overview' },
  { id: 'trends', label: 'Trends' },
  { id: 'seasons', label: 'Seasons' },
  { id: 'states', label: 'States' },
  { id: 'visitors', label: 'Visitors' },
  { id: 'monuments', label: 'Monuments' },
  { id: 'reports', label: 'Reports & PDFs' },
]

/** Official Indian tourism statistics -- a dated snapshot, with sources. */
export function InsightsPage() {
  const { data, isPending, isError } = useInsights()
  const [countryYear, setCountryYear] = useState<2024 | 2025>(2025)

  if (isPending) {
    return (
      <div className="space-y-4">
        <div className="h-40 animate-pulse rounded-2xl bg-slate-200/70" />
        <div className="grid gap-4 sm:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-200/70" />
          ))}
        </div>
      </div>
    )
  }
  if (isError || !data) return <p className="text-sm text-red-700">Could not load the figures.</p>

  const h = data.headline
  const months = data.foreign_arrivals_by_month
  const dtv = data.domestic_visits_by_state
  const ftv = data.foreign_visits_by_state
  const peak = months.rows.find((r) => r.month === h.peak_month)
  const low = months.rows.find((r) => r.month === h.quietest_month)
  const fta = data.foreign_arrivals_by_year
  const fee = data.forex_earnings_by_year
  const dep = data.departures_by_year
  const countries = countryYear === 2025 ? data.source_countries_2025 : data.source_countries_2024
  const countryFmt = countryYear === 2025 ? million : (v: number) => `${count(v)} arrivals`

  const lastFta = fta.rows.at(-1)
  const bestFta = fta.rows.reduce((a, b) => (b.value > a.value ? b : a))
  const bestFee = fee.rows.reduce((a, b) => (b.value > a.value ? b : a))

  return (
    <div className="space-y-10">
      {/* ---------- Hero ---------- */}
      <header className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-600 via-teal-600 to-sky-700 p-6 text-white shadow-lg sm:p-10">
        <div className="pointer-events-none absolute -top-20 -right-20 h-72 w-72 rounded-full bg-white/10 blur-3xl" />
        <div className="relative max-w-3xl">
          <p className="text-sm font-medium text-white/80">📊 Insights · Ministry of Tourism, Government of India</p>
          <h1 className="mt-2 text-3xl font-bold sm:text-4xl">India tourism at a glance</h1>
          <p className="mt-3 text-white/90">
            Official figures on who travels in India, where they go, when they come and what it
            earns — with every number linked to its government source and the full reports to
            download. These figures also shape your plans: the planner knows how busy your
            destination's state and travel month usually are.
          </p>
        </div>
      </header>

      {/* ---------- Section nav ---------- */}
      <nav className="sticky top-16 z-[1000] -mx-4 overflow-x-auto border-y border-slate-200 bg-slate-50/90 px-4 py-2 sm:-mx-6 sm:px-6 lg:-mx-10 lg:px-10 backdrop-blur">
        <ul className="flex gap-1.5 text-sm whitespace-nowrap">
          {SECTIONS.map((s) => (
            <li key={s.id}>
              <a
                href={`#${s.id}`}
                className="block rounded-full px-3.5 py-1.5 text-slate-600 transition hover:bg-white hover:text-slate-900 hover:shadow-sm"
              >
                {s.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      {/* ---------- Overview ---------- */}
      <Section id="overview" title="Overview" sub="The headline numbers.">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Domestic tourist visits"
            value={`${(h.domestic_visits_2024_million / 1000).toFixed(2)} billion`}
            note="2024, all states and UTs"
          />
          <StatTile
            label="Foreign tourist visits"
            value={`${h.foreign_visits_2024_million.toFixed(1)} million`}
            note="2024, all states and UTs"
          />
          <StatTile
            label="Foreign tourist arrivals"
            value={`${h.foreign_arrivals_2025_lakh} lakh`}
            note="2025, into India"
          />
          <StatTile
            label="Busiest month for arrivals"
            value={MONTH_NAMES[h.peak_month]}
            note={`Quietest: ${MONTH_NAMES[h.quietest_month]}`}
          />
          {data.key_facts.rows.map((f) => (
            <StatTile key={f.label} label={f.label} value={f.value} note={f.note || `${data.key_facts.year}`} />
          ))}
        </div>
        <Sources sources={data.key_facts.sources} />

        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-5 py-4">
            <h3 className="text-lg font-semibold">2025 vs 2024</h3>
            <p className="text-sm text-slate-600">What changed in the latest year.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm tabular-nums">
              <thead>
                <tr className="bg-slate-50 text-left text-slate-600">
                  <th className="px-5 py-2 font-medium">Indicator</th>
                  <th className="px-5 py-2 text-right font-medium">2024</th>
                  <th className="px-5 py-2 text-right font-medium">2025</th>
                  <th className="px-5 py-2 text-right font-medium">Change</th>
                </tr>
              </thead>
              <tbody>
                {data.year_on_year.rows.map((r) => (
                  <tr key={r.indicator} className="border-t border-slate-100">
                    <td className="px-5 py-2.5">{r.indicator}</td>
                    <td className="px-5 py-2.5 text-right text-slate-600">{r.y2024}</td>
                    <td className="px-5 py-2.5 text-right font-medium">{r.y2025}</td>
                    <td className="px-5 py-2.5 text-right">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          r.change >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
                        }`}
                      >
                        {r.change >= 0 ? '▲' : '▼'} {Math.abs(r.change).toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-5 pb-4">
            <Sources sources={data.year_on_year.sources} />
          </div>
        </div>
      </Section>

      {/* ---------- Trends ---------- */}
      <Section
        id="trends"
        title="Trends over the years"
        sub="The pandemic dip of 2020–21 and the recovery since."
      >
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartCard
            title="Foreign tourist arrivals"
            subtitle={`Million per year. Record: ${bestFta.year} (${million(bestFta.value)}); latest ${lastFta?.year}: ${lastFta ? million(lastFta.value) : ''}.`}
            sources={fta.sources}
            table={<DataTable head={['Year', 'Arrivals (million)']} rows={fta.rows.map((r) => [r.year, r.value.toFixed(2)])} />}
          >
            <ColumnChart
              data={fta.rows.map((r) => ({ x: String(r.year), y: r.value }))}
              color="var(--viz-foreign)"
              format={million}
              capFormat={(v) => v.toFixed(1)}
              unitLabel="foreign tourist arrivals"
              labelled={[String(bestFta.year), '2021']}
            />
          </ChartCard>

          <ChartCard
            title="Foreign exchange earnings from tourism"
            subtitle={`US$ billion per year. Record: ${bestFee.year} (${usd(bestFee.value)}).`}
            sources={fee.sources}
            table={<DataTable head={['Year', 'US$ billion']} rows={fee.rows.map((r) => [r.year, r.value.toFixed(2)])} />}
          >
            <ColumnChart
              data={fee.rows.map((r) => ({ x: String(r.year), y: r.value }))}
              color="var(--viz-domestic)"
              format={usd}
              capFormat={(v) => v.toFixed(1)}
              unitLabel="tourism forex earnings"
              labelled={[String(bestFee.year), '2021']}
            />
          </ChartCard>
        </div>

        <div className="mt-6">
          <ChartCard
            title="Indians travelling abroad"
            subtitle="Departures of Indian nationals, million per year (2021 not published in this series)."
            sources={dep.sources}
            table={<DataTable head={['Year', 'Departures (million)']} rows={dep.rows.map((r) => [r.year, r.value.toFixed(2)])} />}
          >
            <ColumnChart
              data={dep.rows.map((r) => ({ x: String(r.year), y: r.value }))}
              color="var(--viz-domestic)"
              format={million}
              capFormat={(v) => v.toFixed(1)}
              unitLabel="departures"
              labelled={[String(dep.rows.at(-1)?.year)]}
            />
          </ChartCard>
        </div>
      </Section>

      {/* ---------- Seasons ---------- */}
      <Section id="seasons" title="When visitors come" sub="Plan around the crowds — winter is peak season.">
        <ChartCard
          title="Foreign tourist arrivals by month"
          subtitle={`${months.year}, lakh. Peak ${h.peak_month} ${peak ? lakh(peak.arrivals) : ''}; quietest ${h.quietest_month} ${low ? lakh(low.arrivals) : ''}.`}
          sources={months.sources}
          table={
            <DataTable
              head={['Month', 'Arrivals (lakh)']}
              rows={months.rows.map((r) => [MONTH_NAMES[r.month], r.arrivals.toFixed(2)])}
            />
          }
        >
          <ColumnChart
            data={months.rows.map((r) => ({ x: r.month, y: r.arrivals }))}
            color="var(--viz-foreign)"
            format={lakh}
            capFormat={(v) => v.toFixed(2)}
            unitLabel={`foreign arrivals, ${months.year}`}
            labelled={[h.peak_month, h.quietest_month]}
          />
        </ChartCard>
      </Section>

      {/* ---------- States ---------- */}
      <Section id="states" title="Most-visited states" sub="Visits count a traveller once for every state they visit.">
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartCard
            title="Domestic tourist visits"
            subtitle={`${dtv.year}, million`}
            sources={dtv.sources}
            table={<DataTable head={['State', 'Visits (million)']} rows={dtv.rows.map((r) => [r.state, r.visits.toFixed(2)])} />}
          >
            <BarList
              data={dtv.rows.map((r) => ({ label: r.state, value: r.visits }))}
              color="var(--viz-domestic)"
              format={million}
              describe={(d) => `${d.label} · ${((d.value / h.domestic_visits_2024_million) * 100).toFixed(1)}% of all domestic visits`}
            />
          </ChartCard>

          <ChartCard
            title="Foreign tourist visits"
            subtitle={`${ftv.year}, million`}
            sources={ftv.sources}
            table={<DataTable head={['State', 'Visits (million)']} rows={ftv.rows.map((r) => [r.state, r.visits.toFixed(2)])} />}
          >
            <BarList
              data={ftv.rows.map((r) => ({ label: r.state, value: r.visits }))}
              color="var(--viz-foreign)"
              format={million}
              describe={(d) => `${d.label} · ${((d.value / h.foreign_visits_2024_million) * 100).toFixed(1)}% of all foreign visits`}
            />
          </ChartCard>
        </div>
      </Section>

      {/* ---------- Visitors ---------- */}
      <Section id="visitors" title="Who visits India" sub="Where foreign tourists come from, why, and how they arrive.">
        <ChartCard
          title="Top source countries"
          subtitle={
            countryYear === 2025
              ? 'Foreign tourist arrivals, 2025 (million)'
              : 'Foreign tourist arrivals, 2024 (number of arrivals)'
          }
          sources={countries.sources}
          table={
            <DataTable
              head={['Country', countryYear === 2025 ? 'Arrivals (million)' : 'Arrivals']}
              rows={countries.rows.map((r) => [r.country, countryYear === 2025 ? r.value.toFixed(2) : count(r.value)])}
            />
          }
        >
          <div className="mb-4 inline-flex rounded-lg bg-slate-100 p-1 text-sm">
            {([2025, 2024] as const).map((y) => (
              <button
                key={y}
                type="button"
                onClick={() => setCountryYear(y)}
                className={`rounded-md px-4 py-1 ${countryYear === y ? 'bg-white font-medium shadow-sm' : 'text-slate-600'}`}
              >
                {y}
              </button>
            ))}
          </div>
          <BarList
            data={countries.rows.map((r) => ({ label: r.country, value: r.value }))}
            color="var(--viz-foreign)"
            format={countryFmt}
            describe={(d) => `${d.label} · #${countries.rows.findIndex((r) => r.country === d.label) + 1} source market`}
          />
        </ChartCard>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <ChartCard
            title="Why they came"
            subtitle={`Main purposes of visit, ${data.purpose_of_visit.year} (% of foreign tourist arrivals)`}
            sources={data.purpose_of_visit.sources}
            table={<DataTable head={['Purpose', '%']} rows={data.purpose_of_visit.rows.map((r) => [r.label, r.value.toFixed(2)])} />}
          >
            <BarList
              data={data.purpose_of_visit.rows.map((r) => ({ label: r.label, value: r.value }))}
              color="var(--viz-foreign)"
              format={pct}
              describe={(d) => d.label}
            />
          </ChartCard>

          <ChartCard
            title="Busiest ports of entry"
            subtitle={`Share of foreign tourist arrivals, ${data.ports_of_entry.year}`}
            sources={data.ports_of_entry.sources}
            table={<DataTable head={['Port', '%']} rows={data.ports_of_entry.rows.map((r) => [r.label, r.value.toFixed(1)])} />}
          >
            <BarList
              data={data.ports_of_entry.rows.map((r) => ({ label: r.label, value: r.value }))}
              color="var(--viz-domestic)"
              format={pct}
              describe={(d) => d.label}
            />
          </ChartCard>
        </div>
      </Section>

      {/* ---------- Monuments ---------- */}
      <Section id="monuments" title="Most-visited monuments" sub={`Ticketed ASI monuments, ${data.top_monuments.period}.`}>
        <div className="grid gap-4 sm:grid-cols-3">
          {data.top_monuments.rows.map((m, i) => (
            <div key={m.name} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold text-amber-600">#{i + 1}</p>
              <p className="mt-1 text-lg font-semibold">🏛️ {m.name}</p>
              <p className="text-sm text-slate-500">{m.place}</p>
              <div className="mt-4 flex gap-6 text-sm">
                <div>
                  <p className="text-xl font-bold tabular-nums">{asPublished(m.domestic_m)} M</p>
                  <p className="text-xs text-slate-500">domestic</p>
                </div>
                <div>
                  <p className="text-xl font-bold tabular-nums">{m.foreign_m == null ? '—' : `${asPublished(m.foreign_m)} M`}</p>
                  <p className="text-xs text-slate-500">foreign</p>
                </div>
              </div>
            </div>
          ))}
        </div>
        <Sources sources={data.top_monuments.sources} />
      </Section>

      {/* ---------- Reports ---------- */}
      <Section
        id="reports"
        title="Official reports & PDFs"
        sub="Read the full government publications behind these numbers."
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.reports.map((r) => (
            <ReportCard key={r.url} report={r} />
          ))}
        </div>
      </Section>

      <p className="text-xs text-slate-500">
        “Visits” count a traveller once per state visited; “arrivals” count each entry into India
        once — the two are not comparable. 2025 figures are provisional and may be revised by the
        Ministry.
      </p>
    </div>
  )
}

function Section({
  id,
  title,
  sub,
  children,
}: {
  id: string
  title: string
  sub?: string
  children: React.ReactNode
}) {
  return (
    <section id={id} className="scroll-mt-36">
      <div className="mb-4">
        <h2 className="text-2xl font-bold">{title}</h2>
        {sub && <p className="mt-1 text-slate-600">{sub}</p>}
      </div>
      {children}
    </section>
  )
}

function Sources({ sources }: { sources: Source[] }) {
  return (
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
  )
}

const KIND_STYLE: Record<string, string> = {
  PDF: 'bg-red-50 text-red-700',
  Page: 'bg-sky-50 text-sky-700',
  Portal: 'bg-emerald-50 text-emerald-700',
  'Open data': 'bg-violet-50 text-violet-700',
}
const KIND_ICON: Record<string, string> = { PDF: '📄', Page: '🔗', Portal: '🗂️', 'Open data': '📦' }

function ReportCard({ report }: { report: Report }) {
  return (
    <a
      href={report.url}
      target="_blank"
      rel="noreferrer"
      className="group flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-teal-200 hover:shadow-md"
    >
      <div className="flex items-center justify-between">
        <span className="text-2xl">{KIND_ICON[report.kind] ?? '🔗'}</span>
        <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${KIND_STYLE[report.kind] ?? 'bg-slate-100 text-slate-600'}`}>
          {report.kind}
          {report.year ? ` · ${report.year}` : ''}
        </span>
      </div>
      <p className="mt-3 font-semibold group-hover:text-teal-700">{report.title}</p>
      <p className="mt-1 flex-1 text-sm text-slate-600">{report.about}</p>
      <p className="mt-3 text-sm font-medium text-teal-700">
        {report.kind === 'PDF' ? 'Open PDF ↗' : 'Open ↗'}
      </p>
    </a>
  )
}
