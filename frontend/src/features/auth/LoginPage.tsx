import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { apiErrorMessage, useAuth } from '@/lib/auth'
import { AuthLayout, Field, FormError, SubmitButton } from '@/features/auth/AuthLayout'
import { GoogleButton } from '@/components/GoogleButton'

export function LoginPage() {
  const { isAuthenticated, isLoading, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Where the guard bounced them from, so they land back there after logging in.
  const from = (location.state as { from?: string } | null)?.from ?? '/dashboard'

  // Old links (/login?mode=signup) now go to the separate sign-up page.
  if (new URLSearchParams(location.search).get('mode') === 'signup') {
    return <Navigate to="/signup" replace state={location.state} />
  }
  if (!isLoading && isAuthenticated) return <Navigate to={from} replace />

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const user = await login(email, password)
      // An admin who uses the traveller door still lands in the admin area,
      // unless a guard bounced them here from a specific page.
      const target =
        from !== '/dashboard' ? from : user.role === 'admin' ? '/admin' : user.role === 'business' ? '/business' : from
      navigate(target, { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not log in.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Log in to your trips and plan the next one."
      switchText="New to Safarnama?"
      switchLabel="Create an account"
      switchTo="/signup"
      switchState={location.state}
    >
      <div className="mb-6">
        <GoogleButton redirectTo={from} divider="or log in with email" />
      </div>
      <form onSubmit={handleSubmit} className="space-y-5">
        <Field label="Email address" type="email" icon="mail" value={email} onChange={setEmail} autoComplete="email" />
        <div>
          <Field
            label="Password"
            type="password"
            icon="lock"
            value={password}
            onChange={setPassword}
            autoComplete="current-password"
          />
          <div className="mt-2 text-right">
            <Link to="/forgot-password" className="text-sm font-medium text-slate-600 hover:text-slate-900 hover:underline">
              Forgot password?
            </Link>
          </div>
        </div>
        <FormError message={error} />
        <div className="pt-2">
          <SubmitButton busy={submitting}>Log in</SubmitButton>
        </div>
      </form>
    </AuthLayout>
  )
}
