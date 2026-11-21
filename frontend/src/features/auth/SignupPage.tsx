import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { apiErrorMessage, useAuth, type SignupProfile } from '@/lib/auth'
import { Icon } from '@/components/Icon'
import { AuthLayout, Field, FormError, SubmitButton } from '@/features/auth/AuthLayout'
import { GoogleButton } from '@/components/GoogleButton'
import { CityField, isPickedCity } from '@/components/CityField'
import { GENDERS, INTERESTS, MIN_AGE, ageOf, isoYearsAgo as isoDaysAgo } from '@/features/auth/profileOptions'

const MIN_PASSWORD = 8

const STEPS = ['Account', 'About you', 'Preferences'] as const

function strength(pw: string): { score: number; label: string; color: string } {
  let score = 0
  if (pw.length >= MIN_PASSWORD) score++
  if (pw.length >= 12) score++
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++
  if (/\d/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw)) score++
  if (score <= 1) return { score, label: 'Weak', color: 'bg-red-500' }
  if (score <= 3) return { score, label: 'Fair', color: 'bg-amber-500' }
  return { score, label: 'Strong', color: 'bg-emerald-500' }
}

export function SignupPage() {
  const { isAuthenticated, isLoading, signup } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [step, setStep] = useState(0)
  // step 1
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  // step 2
  const [dob, setDob] = useState('')
  const [homeTown, setHomeTown] = useState('')
  const [phone, setPhone] = useState('')
  const [gender, setGender] = useState<SignupProfile['gender']>()
  // step 3
  const [interests, setInterests] = useState<string[]>([])
  const [agreed, setAgreed] = useState(false)

  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const from = (location.state as { from?: string } | null)?.from ?? '/dashboard'
  if (!isLoading && isAuthenticated) return <Navigate to={from} replace />

  const s = strength(password)

  function validate(current: number): string | null {
    if (current === 0) {
      if (!name.trim()) return 'Please enter your name.'
      if (password.length < MIN_PASSWORD) return `Password must be at least ${MIN_PASSWORD} characters.`
      if (!/[A-Za-z]/.test(password) || !/\d/.test(password))
        return 'Password must contain both letters and numbers.'
      if (password !== confirm) return 'The two passwords do not match.'
    }
    if (current === 1) {
      if (!dob) return 'Please enter your date of birth.'
      const age = ageOf(dob)
      if (age < MIN_AGE) return `You must be at least ${MIN_AGE} years old to sign up.`
      if (age > 120) return 'Please check your date of birth.'
      if (!homeTown.trim()) return 'Please enter your home town.'
      if (!isPickedCity(homeTown)) return 'Pick your home town from the suggestions (City, State).'
      if (phone && !/^\d{10}$/.test(phone.replace(/\s/g, ''))) return 'Enter a 10-digit mobile number, or leave it blank.'
    }
    if (current === 2 && !agreed) return 'Please accept the terms to continue.'
    return null
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const problem = validate(step)
    if (problem) {
      setError(problem)
      return
    }
    setError(null)
    if (step < STEPS.length - 1) {
      setStep(step + 1)
      return
    }

    setSubmitting(true)
    try {
      await signup(name, email, password, {
        date_of_birth: dob,
        home_town: homeTown.trim(),
        phone: phone ? `+91${phone.replace(/\s/g, '')}` : undefined,
        gender,
        travel_interests: interests,
      })
      navigate(from, { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not create the account.'))
      // An email clash is a step-one problem; take them back to fix it.
      if (/email/i.test(String((err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ?? ''))) {
        setStep(0)
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title={['Create your account', 'Tell us about you', 'How do you travel?'][step]}
      subtitle={
        [
          'Free, and it takes less than a minute.',
          'This helps us plan trips that start from home.',
          'Pick what you enjoy — your plans will lean towards it.',
        ][step]
      }
      switchText="Already have an account?"
      switchLabel="Log in"
      switchTo="/login"
      switchState={location.state}
    >
      {step === 0 && (
        <div className="mb-6">
          <GoogleButton redirectTo={from} divider="or sign up with email" />
        </div>
      )}
      <Stepper step={step} />

      <form onSubmit={handleSubmit} noValidate={step !== 0} className="mt-8 space-y-5">
        {step === 0 && (
          <>
            <Field label="Full name" type="text" icon="user" value={name} onChange={setName} autoComplete="name" />
            <Field label="Email address" type="email" icon="mail" value={email} onChange={setEmail} autoComplete="email" />
            <div>
              <Field
                label="Password"
                type="password"
                icon="lock"
                value={password}
                onChange={setPassword}
                autoComplete="new-password"
              />
              <ul className="mt-2.5 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                {[
                  { ok: password.length >= MIN_PASSWORD, label: `${MIN_PASSWORD}+ characters` },
                  { ok: /[A-Za-z]/.test(password), label: 'At least one letter' },
                  { ok: /\d/.test(password), label: 'At least one number' },
                ].map((r) => (
                  <li key={r.label} className={`flex items-center gap-1.5 ${r.ok ? 'text-emerald-600' : 'text-slate-400'}`}>
                    <span
                      className={`flex h-3.5 w-3.5 items-center justify-center rounded-full ${
                        r.ok ? 'bg-emerald-500 text-white' : 'border border-slate-300'
                      }`}
                    >
                      {r.ok && <Icon name="check" className="h-2.5 w-2.5" />}
                    </span>
                    {r.label}
                  </li>
                ))}
              </ul>
              {password && (
                <div className="mt-2.5 flex items-center gap-3">
                  <div className="flex flex-1 gap-1">
                    {[0, 1, 2, 3, 4].map((i) => (
                      <span key={i} className={`h-1 flex-1 rounded-full transition ${i < s.score ? s.color : 'bg-slate-200'}`} />
                    ))}
                  </div>
                  <span className="w-12 text-right text-xs text-slate-500">{s.label}</span>
                </div>
              )}
            </div>
            <Field
              label="Confirm password"
              type="password"
              icon="lock"
              value={confirm}
              onChange={setConfirm}
              autoComplete="new-password"
              error={confirm && confirm !== password ? 'Passwords do not match' : undefined}
            />
          </>
        )}

        {step === 1 && (
          <>
            <div className="grid gap-5 sm:grid-cols-2">
              <Field
                label="Date of birth"
                type="date"
                icon="calendar"
                value={dob}
                onChange={setDob}
                autoComplete="bday"
                max={isoDaysAgo(MIN_AGE)}
                min="1900-01-01"
              />
              <Field
                label="Mobile number"
                type="tel"
                icon="phone"
                prefix="+91"
                value={phone}
                onChange={(v) => setPhone(v.replace(/[^\d\s]/g, '').slice(0, 11))}
                autoComplete="tel-national"
                required={false}
                optional
              />
            </div>
            <CityField label="Home town" value={homeTown} onChange={setHomeTown} hint="Your city — also the starting point for train searches" />
            <fieldset>
              <legend className="mb-2 flex w-full items-baseline justify-between text-sm font-medium text-slate-800">
                Gender
                <span className="text-xs font-normal text-slate-400">Optional</span>
              </legend>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {GENDERS.map((g) => (
                  <button
                    key={g.value}
                    type="button"
                    aria-pressed={gender === g.value}
                    onClick={() => setGender(gender === g.value ? undefined : g.value)}
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
          </>
        )}

        {step === 2 && (
          <>
            <div className="grid grid-cols-2 gap-2.5">
              {INTERESTS.map((it) => {
                const on = interests.includes(it.value)
                return (
                  <button
                    key={it.value}
                    type="button"
                    aria-pressed={on}
                    onClick={() =>
                      setInterests((cur) => (on ? cur.filter((x) => x !== it.value) : [...cur, it.value]))
                    }
                    className={`flex items-center gap-3 rounded-xl border px-4 py-3.5 text-left text-sm transition ${
                      on
                        ? 'border-slate-900 bg-slate-50 font-medium text-slate-900 ring-1 ring-slate-900'
                        : 'border-slate-200 text-slate-700 hover:border-slate-300'
                    }`}
                  >
                    <Icon name={it.icon} className={`h-[18px] w-[18px] ${on ? 'text-indigo-600' : 'text-slate-400'}`} />
                    <span className="flex-1">{it.label}</span>
                    {on && <Icon name="check" className="h-4 w-4 text-slate-900" />}
                  </button>
                )
              })}
            </div>
            <p className="text-xs text-slate-500">Choose any — you can skip this and change it later.</p>

            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 p-4 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                className="mt-0.5 h-4 w-4 accent-slate-900"
              />
              <span>
                I agree to the Terms of Service and Privacy Policy, and I confirm the details above are
                correct.
              </span>
            </label>
          </>
        )}

        <FormError message={error} />

        <div className="flex items-center gap-3 pt-2">
          {step > 0 && (
            <button
              type="button"
              onClick={() => {
                setError(null)
                setStep(step - 1)
              }}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-3.5 text-[15px] font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              <Icon name="back" className="h-4 w-4" />
              Back
            </button>
          )}
          <div className="flex-1">
            <SubmitButton busy={submitting}>{step < STEPS.length - 1 ? 'Continue' : 'Create account'}</SubmitButton>
          </div>
        </div>

        {step === 0 && (
          <p className="text-center text-xs text-slate-400">
            We’ll send a verification email to confirm your address. You can edit your details later in your profile.
          </p>
        )}
      </form>

      {step === 0 && (
        <Link
          to="/signup/business"
          className="mt-8 flex items-center justify-between gap-4 rounded-2xl border border-slate-200 px-5 py-4 transition hover:border-slate-300 hover:bg-slate-50"
        >
          <span className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-white">
              <Icon name="landmark" className="h-5 w-5" />
            </span>
            <span>
              <span className="block text-sm font-semibold text-slate-900">Travel agency or business?</span>
              <span className="block text-xs text-slate-500">Register to publish packages for travellers</span>
            </span>
          </span>
          <Icon name="arrow" className="h-4 w-4 text-slate-400" />
        </Link>
      )}

      <p className="mt-8 text-center text-sm text-slate-500 sm:hidden">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-slate-900">
          Log in
        </Link>
      </p>
    </AuthLayout>
  )
}

function Stepper({ step }: { step: number }) {
  return (
    <ol className="flex items-center gap-3">
      {STEPS.map((label, i) => {
        const done = i < step
        const now = i === step
        return (
          <li key={label} className="flex flex-1 items-center gap-3">
            <span
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold transition ${
                done
                  ? 'bg-slate-900 text-white'
                  : now
                    ? 'border-2 border-slate-900 text-slate-900'
                    : 'border border-slate-200 text-slate-400'
              }`}
            >
              {done ? <Icon name="check" className="h-3.5 w-3.5" /> : i + 1}
            </span>
            <span className={`hidden text-sm sm:block ${now ? 'font-medium text-slate-900' : 'text-slate-400'}`}>
              {label}
            </span>
            {i < STEPS.length - 1 && <span className={`h-px flex-1 ${done ? 'bg-slate-900' : 'bg-slate-200'}`} />}
          </li>
        )
      })}
    </ol>
  )
}
