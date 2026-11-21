import { useState } from 'react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'

export function VerifyEmailBanner() {
  const { user } = useAuth()
  const [state, setState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')

  if (!user || user.is_verified) return null

  async function resend() {
    setState('sending')
    try {
      await api.post('/auth/resend-verification')
      setState('sent')
    } catch {
      setState('error')
    }
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <span>
        Confirm <b>{user.email}</b> to get an email when a plan is ready and a reminder
        before each trip.
      </span>
      {state === 'sent' ? (
        <span>Sent — check your inbox.</span>
      ) : (
        <button
          onClick={resend}
          disabled={state === 'sending'}
          className="rounded border border-amber-300 bg-white px-3 py-1 hover:bg-amber-100 disabled:opacity-50"
        >
          {state === 'sending' ? 'Sending…' : state === 'error' ? 'Try again' : 'Resend email'}
        </button>
      )}
    </div>
  )
}
