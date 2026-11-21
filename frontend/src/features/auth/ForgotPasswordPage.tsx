import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { apiErrorMessage } from '@/lib/auth'
import { Icon } from '@/components/Icon'
import { AuthLayout, Field, FormError, SubmitButton } from '@/features/auth/AuthLayout'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await api.post('/auth/forgot-password', { email })
      setSentTo(email)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not send the reset link. Try again in a minute.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title={sentTo ? 'Check your email' : 'Forgot your password?'}
      subtitle={
        sentTo
          ? 'If an account exists for that address, a reset link is on its way.'
          : 'Enter your email and we’ll send you a link to choose a new one.'
      }
      switchText="Remembered it?"
      switchLabel="Log in"
      switchTo="/login"
    >
      {sentTo ? (
        <div className="space-y-6">
          <div className="flex items-start gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white text-slate-700 ring-1 ring-slate-200">
              <Icon name="mail" className="h-5 w-5" />
            </span>
            <div className="text-sm text-slate-600">
              <p>
                We sent it to <span className="font-medium text-slate-900">{sentTo}</span>. The link works
                once and expires in 30 minutes.
              </p>
              <p className="mt-2">Can’t find it? Check your spam folder.</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/login"
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3.5 text-[15px] font-semibold text-white transition hover:bg-slate-800"
            >
              Back to log in
            </Link>
            <button
              type="button"
              onClick={() => setSentTo(null)}
              className="rounded-xl border border-slate-200 px-5 py-3.5 text-[15px] font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              Use another email
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          <Field label="Email address" type="email" icon="mail" value={email} onChange={setEmail} autoComplete="email" />
          <FormError message={error} />
          <div className="pt-2">
            <SubmitButton busy={submitting}>Send reset link</SubmitButton>
          </div>
          <Link to="/login" className="flex items-center justify-center gap-2 text-sm text-slate-500 hover:text-slate-900">
            <Icon name="back" className="h-4 w-4" /> Back to log in
          </Link>
        </form>
      )}
    </AuthLayout>
  )
}
