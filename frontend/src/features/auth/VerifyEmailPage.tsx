import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '@/lib/api'
import { apiErrorMessage, useAuth, type AuthUser } from '@/lib/auth'

type State =
  | { kind: 'checking' }
  | { kind: 'ok' }
  | { kind: 'error'; message: string }

/**
 * Opened from the link in the verification email. Works logged in or out --
 * the link is often opened on a different device from the one that signed up.
 */
export function VerifyEmailPage() {
  const [params] = useSearchParams()
  const token = params.get('token')
  const { isAuthenticated, updateUser } = useAuth()
  const [state, setState] = useState<State>({ kind: 'checking' })
  const sent = useRef(false)

  useEffect(() => {
    // StrictMode runs effects twice in development; verify once.
    if (sent.current) return
    sent.current = true

    if (!token) {
      setState({ kind: 'error', message: 'This link is missing its token.' })
      return
    }
    api
      .post<AuthUser>('/auth/verify', { token })
      .then(({ data }) => {
        updateUser(data)
        setState({ kind: 'ok' })
      })
      .catch((err) =>
        setState({
          kind: 'error',
          message: apiErrorMessage(err, 'This link could not be used.'),
        }),
      )
  }, [token, updateUser])

  return (
    <section className="mx-auto max-w-sm rounded-lg border border-slate-200 bg-white p-6 text-center">
      {state.kind === 'checking' && <p className="text-slate-600">Confirming your email…</p>}

      {state.kind === 'ok' && (
        <>
          <h1 className="text-xl font-semibold">Email confirmed</h1>
          <p className="mt-2 text-sm text-slate-600">
            You will now get an email when a plan is ready and a reminder before each trip.
          </p>
          <Link
            to={isAuthenticated ? '/dashboard' : '/login'}
            className="mt-6 inline-block rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white"
          >
            {isAuthenticated ? 'Go to dashboard' : 'Log in'}
          </Link>
        </>
      )}

      {state.kind === 'error' && (
        <>
          <h1 className="text-xl font-semibold">Link not valid</h1>
          <p className="mt-2 text-sm text-slate-600">{state.message}</p>
          <p className="mt-2 text-sm text-slate-600">
            Log in and use “Resend email” on your dashboard for a fresh link.
          </p>
        </>
      )}
    </section>
  )
}
