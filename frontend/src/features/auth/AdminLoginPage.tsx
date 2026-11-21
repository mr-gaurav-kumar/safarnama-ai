import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { apiErrorMessage, useAuth } from '@/lib/auth'

/**
 * The admin area's own door. Separate from the traveller login so the two
 * audiences never share a screen -- there is no sign-up here, and an account
 * without the admin role is signed straight back out rather than being let
 * into a shell it cannot use.
 *
 * This is a convenience, not a security boundary: every /admin endpoint
 * re-reads the role from the database on its own.
 */
export function AdminLoginPage() {
  const { isAuthenticated, isAdmin, isLoading, login, logout } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (!isLoading && isAuthenticated && isAdmin) return <Navigate to="/admin" replace />

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const user = await login(email, password)
      if (user.role !== 'admin') {
        await logout()
        setError('That account is not an admin. Use the traveller login instead.')
        return
      }
      navigate('/admin', { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not log in.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="mx-auto max-w-sm rounded-lg border border-slate-700 bg-slate-900 p-6 text-slate-100">
      <h1 className="text-lg font-semibold">Admin sign-in</h1>
      <p className="mt-1 text-sm text-slate-400">
        Staff only. Travellers sign in on the{' '}
        <Link to="/login" className="underline hover:text-slate-200">
          main site
        </Link>
        .
      </p>

      {isAuthenticated && !isAdmin && (
        <p className="mt-4 rounded bg-amber-500/15 px-3 py-2 text-sm text-amber-200">
          You are signed in as a traveller. Sign in with an admin account to continue.
        </p>
      )}

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" />
        <Field
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
        />

        {error && (
          <p role="alert" className="rounded bg-red-500/15 px-3 py-2 text-sm text-red-300">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded bg-white px-4 py-2 text-sm font-medium text-slate-900 hover:bg-slate-200 disabled:opacity-50"
        >
          {submitting ? 'Please wait…' : 'Sign in'}
        </button>
      </form>
    </section>
  )
}

interface FieldProps {
  label: string
  type: string
  value: string
  onChange: (value: string) => void
  autoComplete?: string
}

function Field({ label, type, value, onChange, autoComplete }: FieldProps) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-300">{label}</span>
      <input
        required
        type={type}
        value={value}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 outline-none focus:border-slate-300"
      />
    </label>
  )
}
