import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Icon, LogoMark, type IconName } from '@/components/Icon'

/**
 * Full-height split screen shared by log-in and sign-up: a quiet brand panel
 * on the left, the form on the right.
 */
export function AuthLayout({
  title,
  subtitle,
  switchText,
  switchLabel,
  switchTo,
  switchState,
  children,
}: {
  title: string
  subtitle: string
  switchText: string
  switchLabel: string
  switchTo: string
  switchState?: unknown
  children: ReactNode
}) {
  return (
    <div className="grid min-h-[calc(100dvh-4rem)] bg-white lg:grid-cols-[1fr_1.05fr]">
      <BrandPanel />

      <section className="flex flex-col px-5 py-8 sm:px-12 sm:py-10 lg:px-16">
        <p className="text-right text-sm text-slate-500">
          {switchText}{' '}
          <Link to={switchTo} state={switchState} className="font-semibold text-slate-900 underline-offset-4 hover:underline">
            {switchLabel}
          </Link>
        </p>

        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">
          <h1 className="font-display text-4xl tracking-tight text-slate-950 sm:text-5xl">{title}</h1>
          <p className="mt-3 text-slate-500">{subtitle}</p>
          <div className="mt-10">{children}</div>
        </div>

        <p className="text-center text-xs text-slate-400">
          Protected with hashed passwords and short-lived sessions.
        </p>
      </section>
    </div>
  )
}

function BrandPanel() {
  return (
    <aside className="relative hidden overflow-hidden bg-slate-950 text-white lg:flex lg:flex-col lg:justify-between lg:p-12">
      {/* fine grid + soft glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.07]"
        style={{
          backgroundImage:
            'linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)',
          backgroundSize: '44px 44px',
        }}
      />
      <div aria-hidden className="pointer-events-none absolute -top-40 -left-40 h-[28rem] w-[28rem] rounded-full bg-indigo-600/30 blur-[120px]" />
      <div aria-hidden className="pointer-events-none absolute -right-32 -bottom-40 h-[26rem] w-[26rem] rounded-full bg-sky-500/20 blur-[120px]" />

      <Link to="/" className="relative flex items-center gap-2.5 font-semibold tracking-tight">
        <span className="rounded-lg ring-1 ring-white/20">
          <LogoMark className="h-8 w-auto" tile />
        </span>
        <span>
          Safarnama
          <span className="block text-xs font-normal text-slate-400">Your Next Adventure, Perfectly Planned.</span>
        </span>
      </Link>

      <div className="relative">
        <h2 className="font-display text-5xl leading-[1.05] tracking-tight">
          Travel plans that
          <br />
          <em className="text-indigo-300">know how you travel.</em>
        </h2>
        <p className="mt-5 max-w-sm text-slate-400">
          Day-by-day itineraries shaped by your own trip history, grounded in official tourism data.
        </p>

        {/* A small, calm product glimpse */}
        <div className="mt-10 max-w-sm rounded-2xl border border-white/10 bg-white/[0.04] p-5 backdrop-blur">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Udaipur · Day 2</span>
            <span className="rounded-full bg-emerald-400/10 px-2 py-0.5 text-xs text-emerald-300 ring-1 ring-emerald-400/20">
              Ready
            </span>
          </div>
          <ol className="mt-4 space-y-3 border-l border-white/10 pl-4 text-sm">
            {[
              ['08:30', 'City Palace'],
              ['13:00', 'Lunch by Lake Pichola'],
              ['18:00', 'Sunset at Ambrai Ghat'],
            ].map(([t, p]) => (
              <li key={t} className="relative">
                <span className="absolute top-1.5 -left-[21px] h-2 w-2 rounded-full bg-indigo-400" />
                <span className="mr-2 tabular-nums text-slate-500">{t}</span>
                <span className="text-slate-200">{p}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>

      <div className="relative flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500">
        <span>Ministry of Tourism data</span>
        <span>OpenStreetMap</span>
        <span>IRCTC train search</span>
      </div>
    </aside>
  )
}

/* ------------------------------------------------------------------ */
/*  Form parts                                                         */
/* ------------------------------------------------------------------ */

const inputCls =
  'w-full rounded-xl border border-slate-200 bg-white py-3 text-[15px] text-slate-900 shadow-[0_1px_2px_rgba(15,23,42,0.04)] outline-none transition placeholder:text-slate-400 hover:border-slate-300 focus:border-slate-900 focus:ring-4 focus:ring-slate-900/5'

interface FieldProps {
  label: string
  type: string
  value: string
  onChange: (value: string) => void
  autoComplete?: string
  hint?: string
  icon?: IconName
  required?: boolean
  optional?: boolean
  error?: string
  prefix?: string
  max?: string
  min?: string
  list?: string
}

export function Field({
  label,
  type,
  value,
  onChange,
  autoComplete,
  hint,
  icon,
  required = true,
  optional,
  error,
  prefix,
  max,
  min,
  list,
}: FieldProps) {
  const [show, setShow] = useState(false)
  const isPassword = type === 'password'
  const padLeft = prefix ? 'pl-[4.25rem]' : icon ? 'pl-11' : 'pl-4'
  return (
    <label className="block">
      <span className="mb-2 flex items-baseline justify-between text-sm font-medium text-slate-800">
        {label}
        {optional && <span className="text-xs font-normal text-slate-400">Optional</span>}
      </span>
      <span className="relative block">
        {icon && !prefix && (
          <span className="pointer-events-none absolute top-1/2 left-4 -translate-y-1/2 text-slate-400">
            <Icon name={icon} className="h-[18px] w-[18px]" />
          </span>
        )}
        {prefix && (
          <span className="pointer-events-none absolute top-1/2 left-4 flex -translate-y-1/2 items-center gap-2 text-[15px] text-slate-500">
            {icon && <Icon name={icon} className="h-[18px] w-[18px] text-slate-400" />}
            {prefix}
          </span>
        )}
        <input
          required={required}
          type={isPassword && show ? 'text' : type}
          value={value}
          autoComplete={autoComplete}
          max={max}
          min={min}
          list={list}
          onChange={(e) => onChange(e.target.value)}
          aria-invalid={!!error}
          className={`${inputCls} ${padLeft} ${isPassword ? 'pr-12' : 'pr-4'} ${
            error ? 'border-red-300 focus:border-red-500 focus:ring-red-500/10' : ''
          }`}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            aria-label={show ? 'Hide password' : 'Show password'}
            className="absolute top-1/2 right-3 -translate-y-1/2 rounded-md p-1.5 text-slate-400 hover:text-slate-700"
          >
            <Icon name={show ? 'eyeOff' : 'eye'} className="h-[18px] w-[18px]" />
          </button>
        )}
      </span>
      {error ? (
        <span className="mt-1.5 block text-xs text-red-600">{error}</span>
      ) : (
        hint && <span className="mt-1.5 block text-xs text-slate-500">{hint}</span>
      )}
    </label>
  )
}

export function SubmitButton({ busy, children }: { busy: boolean; children: ReactNode }) {
  return (
    <button
      type="submit"
      disabled={busy}
      className="group inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3.5 text-[15px] font-semibold text-white shadow-[0_1px_2px_rgba(15,23,42,0.2),inset_0_1px_0_rgba(255,255,255,0.1)] transition hover:bg-slate-800 disabled:opacity-50"
    >
      {busy ? (
        <>
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
          Please wait
        </>
      ) : (
        <>
          {children}
          <Icon name="arrow" className="h-4 w-4 transition group-hover:translate-x-0.5" />
        </>
      )}
    </button>
  )
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {message}
    </p>
  )
}
