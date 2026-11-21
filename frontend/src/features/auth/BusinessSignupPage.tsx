import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { apiErrorMessage, useAuth, type BusinessSignup } from '@/lib/auth'
import { Icon } from '@/components/Icon'
import { AuthLayout, Field, FormError, SubmitButton } from '@/features/auth/AuthLayout'
import { CityField, isPickedCity } from '@/components/CityField'

const KINDS: { value: BusinessSignup['kind']; label: string }[] = [
  { value: 'agency', label: 'Travel agency' },
  { value: 'tour_operator', label: 'Tour operator' },
  { value: 'hotel', label: 'Hotel / stay' },
  { value: 'other', label: 'Other' },
]

const STEPS = ['Your account', 'Your business'] as const

export function BusinessSignupPage() {
  const { isAuthenticated, isLoading, signupBusiness } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')

  const [businessName, setBusinessName] = useState('')
  const [kind, setKind] = useState<BusinessSignup['kind']>('agency')
  const [city, setCity] = useState('')
  const [phone, setPhone] = useState('')
  const [website, setWebsite] = useState('')
  const [gst, setGst] = useState('')
  const [description, setDescription] = useState('')
  const [agreed, setAgreed] = useState(false)

  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (!isLoading && isAuthenticated) return <Navigate to="/business" replace />

  function check(): string | null {
    if (step === 0) {
      if (!name.trim()) return 'Enter your name.'
      if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password))
        return 'Password must be at least 8 characters, with letters and numbers.'
      if (password !== confirm) return 'The two passwords do not match.'
    } else {
      if (businessName.trim().length < 2) return 'Enter your business name.'
      if (city.trim().length < 2) return 'Enter the city you operate from.'
      if (!isPickedCity(city)) return 'Pick your city from the suggestions (City, State).'
      if (!/^\d{10}$/.test(phone.replace(/\s/g, ''))) return 'Enter a 10-digit business phone number.'
      if (gst && !/^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/.test(gst.trim().toUpperCase()))
        return 'That GSTIN doesn’t look right — check it or leave it blank.'
      if (!agreed) return 'Please accept the terms to continue.'
    }
    return null
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    const problem = check()
    if (problem) return setError(problem)
    setError(null)
    if (step === 0) return setStep(1)
    setSubmitting(true)
    try {
      await signupBusiness({
        name: name.trim(), email, password,
        business_name: businessName.trim(), kind, city: city.trim(),
        business_phone: `+91${phone.replace(/\s/g, '')}`,
        website: website.trim() || undefined,
        gst_number: gst.trim() || undefined,
        description: description.trim() || undefined,
      })
      navigate('/business', { replace: true })
    } catch (err) {
      const msg = apiErrorMessage(err, 'Could not register the business.')
      setError(msg)
      if (/email|password/i.test(msg)) setStep(0)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title={step === 0 ? 'Register your business' : 'About your business'}
      subtitle={
        step === 0
          ? 'For travel agencies, tour operators and hotels. Publish packages that every traveller can book.'
          : 'Our team reviews every business before its packages go live — usually within a day.'
      }
      switchText="Just travelling?"
      switchLabel="Sign up as a traveller"
      switchTo="/signup"
    >
      <ol className="flex items-center gap-3">
        {STEPS.map((label, i) => (
          <li key={label} className="flex flex-1 items-center gap-3">
            <span
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                i < step ? 'bg-slate-900 text-white' : i === step ? 'border-2 border-slate-900' : 'border border-slate-200 text-slate-400'
              }`}
            >
              {i < step ? <Icon name="check" className="h-3.5 w-3.5" /> : i + 1}
            </span>
            <span className={`hidden text-sm sm:block ${i === step ? 'font-medium' : 'text-slate-400'}`}>{label}</span>
            {i < STEPS.length - 1 && <span className={`h-px flex-1 ${i < step ? 'bg-slate-900' : 'bg-slate-200'}`} />}
          </li>
        ))}
      </ol>

      <form onSubmit={submit} noValidate={step === 1} className="mt-8 space-y-5">
        {step === 0 ? (
          <>
            <Field label="Your full name" type="text" icon="user" value={name} onChange={setName} autoComplete="name" />
            <Field label="Work email" type="email" icon="mail" value={email} onChange={setEmail} autoComplete="email" />
            <Field
              label="Password"
              type="password"
              icon="lock"
              value={password}
              onChange={setPassword}
              autoComplete="new-password"
              hint="At least 8 characters, with letters and numbers"
            />
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
        ) : (
          <>
            <Field label="Business name" type="text" icon="landmark" value={businessName} onChange={setBusinessName} autoComplete="organization" />
            <fieldset>
              <legend className="mb-2 text-sm font-medium text-slate-800">Type of business</legend>
              <div className="grid grid-cols-2 gap-2">
                {KINDS.map((k) => (
                  <button
                    key={k.value}
                    type="button"
                    aria-pressed={kind === k.value}
                    onClick={() => setKind(k.value)}
                    className={`rounded-xl border px-3 py-2.5 text-sm transition ${
                      kind === k.value ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 text-slate-700 hover:border-slate-300'
                    }`}
                  >
                    {k.label}
                  </button>
                ))}
              </div>
            </fieldset>
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <CityField label="City you operate from" value={city} onChange={setCity} />
              </div>
              <Field
                label="Business phone"
                type="tel"
                icon="phone"
                prefix="+91"
                value={phone}
                onChange={(v) => setPhone(v.replace(/[^\d\s]/g, '').slice(0, 11))}
              />
              <Field label="Website" type="text" icon="map" value={website} onChange={setWebsite} required={false} optional />
              <Field
                label="GSTIN"
                type="text"
                icon="file"
                value={gst}
                onChange={(v) => setGst(v.toUpperCase().slice(0, 15))}
                required={false}
                optional
              />
            </div>
            <label className="block">
              <span className="mb-2 flex items-baseline justify-between text-sm font-medium text-slate-800">
                About your business <span className="text-xs font-normal text-slate-400">Optional</span>
              </span>
              <textarea
                rows={3}
                maxLength={2000}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What you specialise in, since when, where you operate…"
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-[15px] outline-none focus:border-slate-900 focus:ring-4 focus:ring-slate-900/5"
              />
            </label>
            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 p-4 text-sm text-slate-600">
              <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} className="mt-0.5 h-4 w-4 accent-slate-900" />
              <span>
                I confirm these details are accurate, I’m authorised to represent this business, and I agree to the
                Partner Terms.
              </span>
            </label>
          </>
        )}

        <FormError message={error} />

        <div className="flex items-center gap-3 pt-2">
          {step > 0 && (
            <button
              type="button"
              onClick={() => { setError(null); setStep(0) }}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-3.5 text-[15px] font-medium text-slate-700 hover:bg-slate-50"
            >
              <Icon name="back" className="h-4 w-4" /> Back
            </button>
          )}
          <div className="flex-1">
            <SubmitButton busy={submitting}>{step === 0 ? 'Continue' : 'Submit for approval'}</SubmitButton>
          </div>
        </div>
      </form>
    </AuthLayout>
  )
}
