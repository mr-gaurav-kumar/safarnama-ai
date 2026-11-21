import type { ReactNode } from 'react'

interface PlaceholderProps {
  title: string
  phase: string
  children?: ReactNode
}

/** Stands in for a page that is scheduled but not built yet. */
export function Placeholder({ title, phase, children }: PlaceholderProps) {
  return (
    <section className="rounded-lg border border-dashed border-slate-300 bg-white p-8">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="mt-1 text-sm text-slate-500">Scheduled for {phase}.</p>
      {children && <div className="mt-4 text-sm">{children}</div>}
    </section>
  )
}
