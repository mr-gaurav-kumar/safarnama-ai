/**
 * The small set of pieces every admin table is built from. Kept here so the
 * seven screens stay thin and look like one product rather than seven.
 */
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { apiErrorMessage } from '@/lib/auth'

// --- paging ----------------------------------------------------------------

export interface Paged {
  limit: number
  offset: number
  page: number
  setPage: (n: number) => void
  /** Resets to the first page -- call it whenever a filter changes, or a
   *  search on page 4 shows "no results" for rows that are on page 1. */
  reset: () => void
}

export function usePaged(limit = 25): Paged {
  const [page, setPage] = useState(0)
  return useMemo(
    () => ({
      limit,
      offset: page * limit,
      page,
      setPage,
      reset: () => setPage(0),
    }),
    [limit, page],
  )
}

/** Debounces a search box so typing does not fire a request per keystroke. */
export function useDebounced<T>(value: T, ms = 300): T {
  const [settled, setSettled] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setSettled(value), ms)
    return () => clearTimeout(id)
  }, [value, ms])
  return settled
}

export function Pagination({ total, paged }: { total: number; paged: Paged }) {
  const { limit, offset, page, setPage } = paged
  const last = Math.max(0, Math.ceil(total / limit) - 1)
  const from = total === 0 ? 0 : offset + 1
  const to = Math.min(offset + limit, total)

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-sm text-slate-600">
      <span>
        {from}-{to} of {total}
      </span>
      <div className="flex gap-2">
        <button
          onClick={() => setPage(page - 1)}
          disabled={page <= 0}
          className="rounded border border-slate-300 px-3 py-1 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Previous
        </button>
        <button
          onClick={() => setPage(page + 1)}
          disabled={page >= last}
          className="rounded border border-slate-300 px-3 py-1 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  )
}

// --- page furniture --------------------------------------------------------

export function PageHeader({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children?: ReactNode
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-600">{subtitle}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </header>
  )
}

export function SearchBox({
  value,
  onChange,
  placeholder,
}: {
  value: string
  onChange: (v: string) => void
  placeholder: string
}) {
  return (
    <input
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full rounded border border-slate-300 px-3 py-2 text-sm sm:w-72"
    />
  )
}

export function Filter<T extends string>({
  value,
  onChange,
  options,
  label,
}: {
  value: T
  onChange: (v: T) => void
  options: { value: T; label: string }[]
  label: string
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-slate-600">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className="rounded border border-slate-300 px-2 py-2 text-sm text-slate-900"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  )
}

// --- table -----------------------------------------------------------------

/** A card with a scrolling table inside. Columns are plain <th>/<td>. */
export function TableCard({
  head,
  children,
  isPending,
  isError,
  isEmpty,
  emptyText,
  colSpan,
  footer,
}: {
  head: ReactNode
  children: ReactNode
  isPending: boolean
  isError: boolean
  isEmpty: boolean
  emptyText: string
  colSpan: number
  footer?: ReactNode
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[42rem] text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            {head}
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isPending && (
              <tr>
                <td colSpan={colSpan} className="px-4 py-8 text-center text-slate-500">
                  Loading…
                </td>
              </tr>
            )}
            {isError && (
              <tr>
                <td colSpan={colSpan} className="px-4 py-8 text-center text-red-700">
                  Could not load this list.
                </td>
              </tr>
            )}
            {!isPending && !isError && isEmpty && (
              <tr>
                <td colSpan={colSpan} className="px-4 py-8 text-center text-slate-500">
                  {emptyText}
                </td>
              </tr>
            )}
            {children}
          </tbody>
        </table>
      </div>
      {footer}
    </div>
  )
}

export function Th({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <th className={`px-4 py-3 font-medium ${className}`}>{children}</th>
}

export function Td({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <td className={`px-4 py-3 align-top ${className}`}>{children}</td>
}

// --- badges ----------------------------------------------------------------

type Tone = 'neutral' | 'good' | 'warn' | 'bad' | 'info'

const TONES: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-slate-700',
  good: 'bg-emerald-100 text-emerald-800',
  warn: 'bg-amber-100 text-amber-900',
  bad: 'bg-red-100 text-red-800',
  info: 'bg-sky-100 text-sky-800',
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: Tone }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  )
}

/** One place that decides what colour a status word gets, so "failed" looks
 *  the same on the trips table and the fraud table. */
export function StatusBadge({ status }: { status: string }) {
  const tone: Tone =
    status === 'completed' || status === 'resolved'
      ? 'good'
      : status === 'processing' || status === 'open'
        ? 'warn'
        : status === 'failed'
          ? 'bad'
          : status === 'dismissed'
            ? 'neutral'
            : 'info'
  return <Badge tone={tone}>{status}</Badge>
}

// --- buttons ---------------------------------------------------------------

export function Button({
  children,
  onClick,
  disabled,
  variant = 'ghost',
  type = 'button',
}: {
  children: ReactNode
  onClick?: () => void
  disabled?: boolean
  variant?: 'primary' | 'ghost' | 'danger'
  type?: 'button' | 'submit'
}) {
  const styles = {
    primary: 'bg-slate-900 text-white hover:bg-slate-800',
    ghost: 'border border-slate-300 text-slate-700 hover:bg-slate-100',
    danger: 'border border-red-300 text-red-700 hover:bg-red-50',
  }[variant]
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`whitespace-nowrap rounded px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${styles}`}
    >
      {children}
    </button>
  )
}

/**
 * A destructive action that asks first, inline. Deliberately not window.confirm:
 * a native dialog blocks the page, and in an embedded browser it can block the
 * whole session.
 */
export function ConfirmButton({
  children,
  confirmLabel = 'Confirm',
  onConfirm,
  disabled,
}: {
  children: ReactNode
  confirmLabel?: string
  onConfirm: () => void
  disabled?: boolean
}) {
  const [armed, setArmed] = useState(false)

  // Disarm after a few seconds so a half-pressed delete does not sit waiting.
  useEffect(() => {
    if (!armed) return
    const id = setTimeout(() => setArmed(false), 5000)
    return () => clearTimeout(id)
  }, [armed])

  if (!armed) {
    return (
      <Button variant="danger" onClick={() => setArmed(true)} disabled={disabled}>
        {children}
      </Button>
    )
  }
  return (
    <span className="inline-flex gap-1">
      <Button variant="danger" onClick={() => { setArmed(false); onConfirm() }} disabled={disabled}>
        {confirmLabel}
      </Button>
      <Button onClick={() => setArmed(false)}>Cancel</Button>
    </span>
  )
}

// --- errors ----------------------------------------------------------------

export function ErrorNote({ error, fallback }: { error: unknown; fallback: string }) {
  if (!error) return null
  return (
    <p className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
      {apiErrorMessage(error, fallback)}
    </p>
  )
}
