import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '@/lib/api'
import { Icon } from '@/components/Icon'
import { coverTone, mediaUrl } from '@/lib/media'
import type { TravelPackage } from '@/features/admin/types'

interface PublicBusiness {
  business: { business_name: string; slug: string; kind: string; city: string; description: string; website: string | null; since: string }
  packages: TravelPackage[]
}

const KIND: Record<string, string> = {
  agency: 'Travel agency', tour_operator: 'Tour operator', hotel: 'Hotel / stay', other: 'Travel business',
}
const INR = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

/** Shareable page for one business: who they are and everything they offer. */
export function BusinessPublicPage() {
  const { slug } = useParams<{ slug: string }>()
  const { data, isPending, isError } = useQuery({
    queryKey: ['public-business', slug],
    queryFn: async () => (await api.get<PublicBusiness>(`/businesses/${slug}`)).data,
    enabled: !!slug,
  })

  if (isPending) return <div className="h-64 animate-pulse rounded-3xl bg-slate-200/60" />
  if (isError || !data) {
    return (
      <p className="text-sm text-slate-600">
        This business page isn’t available. <Link to="/packages" className="underline">Browse all packages</Link>
      </p>
    )
  }
  const b = data.business
  const initials = b.business_name.split(/\s+/).map((p) => p[0]).join('').slice(0, 2).toUpperCase()

  return (
    <div className="space-y-10">
      <header className="relative overflow-hidden rounded-3xl bg-ink px-6 py-10 text-white sm:px-10 sm:py-14">
        <div aria-hidden className="pointer-events-none absolute -top-32 -right-24 h-96 w-96 rounded-full bg-gold/25 blur-[110px]" />
        <div aria-hidden className="pointer-events-none absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-gold/60 to-transparent" />
        <div className="relative flex flex-wrap items-center gap-6">
          <span className="flex h-20 w-20 items-center justify-center rounded-2xl bg-white/5 text-2xl font-semibold text-gold-light ring-1 ring-gold/40">
            {initials}
          </span>
          <div className="min-w-0">
            <p className="text-xs font-semibold tracking-[0.2em] text-gold uppercase">{KIND[b.kind] ?? 'Travel business'}</p>
            <h1 className="font-display mt-2 text-4xl leading-tight tracking-tight sm:text-5xl">{b.business_name}</h1>
            <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-400">
              <span className="flex items-center gap-1.5"><Icon name="pin" className="h-4 w-4" /> {b.city}</span>
              <span>On Safarnama since {new Date(b.since).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}</span>
              <span className="flex items-center gap-1.5 text-emerald-300"><Icon name="shield" className="h-4 w-4" /> Verified partner</span>
            </p>
          </div>
        </div>
        {b.description && <p className="relative mt-6 max-w-3xl whitespace-pre-line text-slate-300">{b.description}</p>}
        {b.website && (
          <a href={b.website} target="_blank" rel="noreferrer" className="relative mt-6 inline-flex items-center gap-2 text-sm font-medium text-gold-light hover:text-white">
            Visit website <Icon name="arrow" className="h-4 w-4" />
          </a>
        )}
      </header>

      <section>
        <h2 className="font-display text-3xl tracking-tight">Packages by {b.business_name}</h2>
        {data.packages.length === 0 ? (
          <p className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
            No packages published yet.
          </p>
        ) : (
          <div className="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {data.packages.map((p) => (
              <Link key={p.id} to={`/packages/${p.id}`} className="group flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:border-slate-300 hover:shadow-md">
                <div className={`h-40 bg-gradient-to-br ${coverTone(p.title)}`}>
                  {p.images?.[0] && <img src={mediaUrl(p.images[0])} alt="" className="h-full w-full object-cover" loading="lazy" />}
                </div>
                <div className="flex flex-1 flex-col p-6">
                <p className="flex items-center gap-1.5 text-xs text-slate-500"><Icon name="pin" className="h-3.5 w-3.5" /> {p.destination}</p>
                <h3 className="font-display mt-2 text-2xl leading-tight tracking-tight">{p.title}</h3>
                {p.summary && <p className="mt-2 line-clamp-2 text-sm text-slate-600">{p.summary}</p>}
                <div className="mt-auto flex items-end justify-between pt-6">
                  <p className="text-lg font-semibold">{INR.format(p.price_per_person)}<span className="text-sm font-normal text-slate-500"> / person · {p.duration_days} days</span></p>
                  <Icon name="arrow" className="h-4 w-4 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-slate-900" />
                </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
