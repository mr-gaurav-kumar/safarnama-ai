import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { apiErrorMessage } from '@/lib/auth'
import { useDecline, useJoin } from '@/features/trips/groupApi'

/** Opened from an invitation email: /join?trip=<id>&token=<token>. */
export function JoinPage() {
  const [params] = useSearchParams()
  const tripId = params.get('trip') ?? ''
  const token = params.get('token')
  const join = useJoin(tripId)
  const decline = useDecline(tripId)
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [declined, setDeclined] = useState(false)
  const busy = useRef(false)

  useEffect(() => {
    if (!tripId || !token) setError('This invitation link is incomplete.')
  }, [tripId, token])

  async function accept() {
    if (busy.current) return
    busy.current = true
    setError(null)
    try {
      await join.mutateAsync(token)
      navigate(`/trips/${tripId}`, { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err, 'This invitation could not be used.'))
    } finally {
      busy.current = false
    }
  }

  async function no() {
    setError(null)
    try {
      await decline.mutateAsync(token)
      setDeclined(true)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not decline.'))
    }
  }

  return (
    <section className="mx-auto max-w-sm rounded-lg border border-slate-200 bg-white p-6 text-center">
      {declined ? (
        <>
          <h1 className="text-xl font-semibold">Invitation declined</h1>
          <Link to="/dashboard" className="mt-4 inline-block text-sm underline">Back to dashboard</Link>
        </>
      ) : (
        <>
          <h1 className="text-xl font-semibold">Join this trip?</h1>
          <p className="mt-2 text-sm text-slate-600">
            You'll see the plan, chat with the group and add what you'd like to do.
          </p>
          <div className="mt-5 flex justify-center gap-3">
            <button
              onClick={accept}
              disabled={!token || join.isPending}
              className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {join.isPending ? 'Joining…' : 'Join'}
            </button>
            <button
              onClick={no}
              disabled={!token || decline.isPending}
              className="rounded border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
            >
              Decline
            </button>
          </div>
          {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
        </>
      )}
    </section>
  )
}
