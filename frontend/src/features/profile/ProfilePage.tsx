import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { TicketsCard } from '@/features/tickets/TicketsCard'
import { AvatarEditor } from '@/features/profile/AvatarEditor'
import { DocumentsCard } from '@/features/profile/DocumentsCard'
import { api } from '@/lib/api'
import { apiErrorMessage, useAuth, type AuthUser } from '@/lib/auth'
import { Icon } from '@/components/Icon'
import { Field, FormError } from '@/features/auth/AuthLayout'
import { CityField, isPickedCity } from '@/components/CityField'
import { GENDERS, INTERESTS, MIN_AGE, ageOf, isoYearsAgo } from '@/features/auth/profileOptions'

/** The phone is stored as +91XXXXXXXXXX; the form shows the 10 digits. */
function localPhone(stored?: string | null): string {
  if (!stored) return ''
  return stored.startsWith('+91') ? stored.slice(3) : stored
}

export function ProfilePage() {
  const { user, updateUser } = useAuth()

  const [name, setName] = useState('')
  const [dob, setDob] = useState('')
  const [homeTown, setHomeTown] = useState('')
  const [phone, setPhone] = useState('')
  const [gender, setGender] = useState<string | null>(null)
  const [interests, setInterests] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fill the form from the latest server copy of the account.
  useEffect(() => {
    let cancelled = false
    api.get<AuthUser>('/auth/me').then(({ data }) => {
      if (cancelled) return
      updateUser(data)
      setName(data.name ?? '')
      setDob(data.date_of_birth ?? '')
      setHomeTown(data.home_town ?? '')
      setPhone(localPhone(data.phone))
      setGender(data.gender ?? null)
      setInterests(data.travel_interests ?? [])
    }).catch(() => {
      /* keep what the session already has */
    })
    return () => {
      cancelled = true
    }
  }, [updateUser])

  if (!user) return null

  async function saveProfile(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSaved(false)
    if (!name.trim()) return setError('Name cannot be empty.')
    if (dob && ageOf(dob) < MIN_AGE) return setError(`You must be at least ${MIN_AGE} years old.`)
    if (homeTown.trim() && !isPickedCity(homeTown)) return setError('Pick your home town from the suggestions (City, State).')
    const digits = phone.replace(/\s/g, '')
    if (digits && !/^\d{10}$/.test(digits)) return setError('Enter a 10-digit mobile number, or leave it blank.')

    setSaving(true)
    try {
      const { data } = await api.put<AuthUser>('/auth/me', {
        name: name.trim(),
        date_of_birth: dob || null,
        home_town: homeTown.trim() || null,
        phone: digits ? `+91${digits}` : null,
        gender: gender || null,
        travel_interests: interests,
      })
      updateUser(data)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not save your profile.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      {/* ---------- Header ---------- */}
      <header className="flex flex-wrap items-center gap-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <AvatarEditor />
        <div className="min-w-0 flex-1">
          <h1 className="font-display text-4xl tracking-tight">{user.name}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-500">
            {user.email}
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${
                user.is_verified
                  ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                  : 'bg-amber-50 text-amber-700 ring-amber-200'
              }`}
            >
              {user.is_verified ? 'Verified' : 'Email not verified'}
            </span>
            {user.role === 'admin' && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-slate-200">
                Admin
              </span>
            )}
          </p>
        </div>
      </header>

      {/* ---------- Personal details ---------- */}
      <form onSubmit={saveProfile} noValidate>
        <Card
          title="Personal details"
          sub="Your home town is used as the starting point for train searches."
          footer={
            <div className="flex items-center justify-end gap-4">
              {saved && (
                <span className="flex items-center gap-1.5 text-sm text-emerald-700">
                  <Icon name="check" className="h-4 w-4" /> Saved
                </span>
              )}
              <button
                type="submit"
                disabled={saving}
                className="rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          }
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Full name" type="text" icon="user" value={name} onChange={setName} autoComplete="name" />
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-800">Email address</span>
              <span className="relative block">
                <span className="pointer-events-none absolute top-1/2 left-4 -translate-y-1/2 text-slate-400">
                  <Icon name="mail" className="h-[18px] w-[18px]" />
                </span>
                <input
                  value={user.email}
                  disabled
                  className="w-full cursor-not-allowed rounded-xl border border-slate-200 bg-slate-50 py-3 pr-4 pl-11 text-[15px] text-slate-500"
                />
              </span>
              <span className="mt-1.5 block text-xs text-slate-500">Email can’t be changed.</span>
            </label>
            <Field
              label="Date of birth"
              type="date"
              icon="calendar"
              value={dob}
              onChange={setDob}
              required={false}
              max={isoYearsAgo(MIN_AGE)}
              min="1900-01-01"
            />
            <Field
              label="Mobile number"
              type="tel"
              icon="phone"
              prefix="+91"
              value={phone}
              onChange={(v) => setPhone(v.replace(/[^\d\s]/g, '').slice(0, 11))}
              required={false}
              optional
            />
            <div className="sm:col-span-2">
              <CityField label="Home town" value={homeTown} onChange={setHomeTown} required={false} hint="Type a few letters and pick your city" />
            </div>
          </div>

          <fieldset className="mt-6">
            <legend className="mb-2 text-sm font-medium text-slate-800">Gender</legend>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {GENDERS.map((g) => (
                <button
                  key={g.value}
                  type="button"
                  aria-pressed={gender === g.value}
                  onClick={() => setGender(gender === g.value ? null : g.value)}
                  className={`rounded-xl border px-3 py-2.5 text-sm transition ${
                    gender === g.value
                      ? 'border-slate-900 bg-slate-900 text-white'
                      : 'border-slate-200 text-slate-700 hover:border-slate-300'
                  }`}
                >
                  {g.label}
                </button>
              ))}
            </div>
          </fieldset>

          <fieldset className="mt-6">
            <legend className="mb-2 text-sm font-medium text-slate-800">Travel interests</legend>
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
              {INTERESTS.map((it) => {
                const on = interests.includes(it.value)
                return (
                  <button
                    key={it.value}
                    type="button"
                    aria-pressed={on}
                    onClick={() => setInterests((cur) => (on ? cur.filter((x) => x !== it.value) : [...cur, it.value]))}
                    className={`flex items-center gap-2.5 rounded-xl border px-3.5 py-3 text-left text-sm transition ${
                      on
                        ? 'border-slate-900 bg-slate-50 font-medium text-slate-900 ring-1 ring-slate-900'
                        : 'border-slate-200 text-slate-700 hover:border-slate-300'
                    }`}
                  >
                    <Icon name={it.icon} className={`h-[18px] w-[18px] ${on ? 'text-indigo-600' : 'text-slate-400'}`} />
                    <span className="flex-1">{it.label}</span>
                  </button>
                )
              })}
            </div>
          </fieldset>

          <div className="mt-6">
            <FormError message={error} />
          </div>
        </Card>
      </form>

      <TicketsCard />

      <DocumentsCard />

      <ChangePasswordCard />
    </div>
  )
}

function Card({
  title,
  sub,
  children,
  footer,
}: {
  title: string
  sub?: string
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-6 py-5 sm:px-8">
        <h2 className="text-lg font-semibold">{title}</h2>
        {sub && <p className="mt-0.5 text-sm text-slate-500">{sub}</p>}
      </div>
      <div className="px-6 py-6 sm:px-8">{children}</div>
      {footer && <div className="border-t border-slate-100 bg-slate-50/60 px-6 py-4 sm:px-8">{footer}</div>}
    </section>
  )
}

function ChangePasswordCard() {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)

  const rules = [
    { ok: next.length >= 8, label: '8+ characters' },
    { ok: /[A-Za-z]/.test(next), label: 'A letter' },
    { ok: /\d/.test(next), label: 'A number' },
  ]

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setDone(null)
    if (!rules.every((r) => r.ok)) return setError('New password must be at least 8 characters, with letters and numbers.')
    if (next !== confirm) return setError('The new passwords do not match.')
    setBusy(true)
    try {
      const { data } = await api.post<{ detail: string }>('/auth/change-password', {
        current_password: current,
        new_password: next,
      })
      setDone(data.detail)
      setCurrent('')
      setNext('')
      setConfirm('')
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not change the password.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate>
      <Card
        title="Password"
        sub="Changing it signs you out on every other device."
        footer={
          <div className="flex items-center justify-end gap-4">
            {done && (
              <span className="flex items-center gap-1.5 text-sm text-emerald-700">
                <Icon name="check" className="h-4 w-4" /> {done}
              </span>
            )}
            <button
              type="submit"
              disabled={busy || !current || !next}
              className="rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
            >
              {busy ? 'Updating…' : 'Update password'}
            </button>
          </div>
        }
      >
        <div className="grid gap-5 sm:grid-cols-3">
          <Field label="Current password" type="password" icon="lock" value={current} onChange={setCurrent} autoComplete="current-password" />
          <div>
            <Field label="New password" type="password" icon="lock" value={next} onChange={setNext} autoComplete="new-password" />
            {next && (
              <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs">
                {rules.map((r) => (
                  <li key={r.label} className={`flex items-center gap-1 ${r.ok ? 'text-emerald-600' : 'text-slate-400'}`}>
                    {r.ok ? <Icon name="check" className="h-3 w-3" /> : <span className="h-2 w-2 rounded-full border border-slate-300" />}
                    {r.label}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <Field
            label="Confirm new password"
            type="password"
            icon="lock"
            value={confirm}
            onChange={setConfirm}
            autoComplete="new-password"
            error={confirm && confirm !== next ? 'Does not match' : undefined}
          />
        </div>
        <div className="mt-5">
          <FormError message={error} />
        </div>
      </Card>
    </form>
  )
}
