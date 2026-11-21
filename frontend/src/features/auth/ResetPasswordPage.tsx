import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '@/lib/api'
import { apiErrorMessage } from '@/lib/auth'
import { Icon } from '@/components/Icon'
import { AuthLayout, Field, FormError, SubmitButton } from '@/features/auth/AuthLayout'

const MIN_PASSWORD = 8

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const rules = [
    { ok: password.length >= MIN_PASSWORD, label: `${MIN_PASSWORD}+ characters` },
    { ok: /[A-Za-z]/.test(password), label: 'At least one letter' },
    { ok: /\d/.test(password), label: 'At least one number' },
  ]

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (!rules.every((r) => r.ok)) {
      setError('Password must be at least 8 characters, with letters and numbers.')
      return
    }
    if (password !== confirm) {
      setError('The two passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await api.post('/auth/reset-password', { token, password })
      setDone(true)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not reset the password.'))
    } finally {
      setSubmitting(false)
    }
  }

  if (!token) {
    return (
      <AuthLayout
        title="Link not valid"
        subtitle="This reset link is incomplete. Request a new one."
        switchText="Remembered it?"
        switchLabel="Log in"
        switchTo="/login"
      >
        <Link
          to="/forgot-password"
          className="inline-flex w-full items-center justify-center rounded-xl bg-slate-950 px-4 py-3.5 text-[15px] font-semibold text-white hover:bg-slate-800"
        >
          Request a new link
        </Link>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title={done ? 'Password updated' : 'Choose a new password'}
      subtitle={
        done
          ? 'You’ve been signed out on every device. Log in with your new password.'
          : 'Make it something you haven’t used here before.'
      }
      switchText="Remembered it?"
      switchLabel="Log in"
      switchTo="/login"
    >
      {done ? (
        <div className="space-y-6">
          <div className="flex items-center gap-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-sm text-emerald-800">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white ring-1 ring-emerald-200">
              <Icon name="check" className="h-5 w-5" />
            </span>
            Your password has been changed successfully.
          </div>
          <Link
            to="/login"
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3.5 text-[15px] font-semibold text-white hover:bg-slate-800"
          >
            Log in <Icon name="arrow" className="h-4 w-4" />
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <Field
              label="New password"
              type="password"
              icon="lock"
              value={password}
              onChange={setPassword}
              autoComplete="new-password"
            />
            <ul className="mt-2.5 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              {rules.map((r) => (
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
          </div>
          <Field
            label="Confirm new password"
            type="password"
            icon="lock"
            value={confirm}
            onChange={setConfirm}
            autoComplete="new-password"
            error={confirm && confirm !== password ? 'Passwords do not match' : undefined}
          />
          <FormError message={error} />
          {error && /invalid|expired|used/i.test(error) && (
            <Link to="/forgot-password" className="block text-center text-sm font-semibold text-slate-900 hover:underline">
              Request a new link
            </Link>
          )}
          <div className="pt-2">
            <SubmitButton busy={submitting}>Update password</SubmitButton>
          </div>
        </form>
      )}
    </AuthLayout>
  )
}
