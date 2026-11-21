import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { apiErrorMessage, useAuth } from '@/lib/auth'

/** The bits of Google Identity Services this button uses. */
interface GoogleId {
  initialize: (opts: { client_id: string; callback: (r: { credential: string }) => void; ux_mode?: 'popup' }) => void
  renderButton: (el: HTMLElement, opts: Record<string, unknown>) => void
}
declare global {
  interface Window {
    google?: { accounts: { id: GoogleId } }
  }
}

const GSI_SRC = 'https://accounts.google.com/gsi/client'
let gsiLoading: Promise<void> | null = null

function loadGsi(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve()
  gsiLoading ??= new Promise<void>((resolve, reject) => {
    const s = document.createElement('script')
    s.src = GSI_SRC
    s.async = true
    s.onload = () => resolve()
    s.onerror = () => {
      gsiLoading = null
      reject(new Error('Could not load Google sign-in'))
    }
    document.head.appendChild(s)
  })
  return gsiLoading
}

/**
 * "Continue with Google". Renders nothing until the server says Google
 * sign-in is set up (GOOGLE_CLIENT_ID in .env), so the page never shows a
 * button that cannot work. Google hands the browser a signed ID token; the
 * backend verifies it -- the browser's word is never taken for who you are.
 */
export function GoogleButton({ redirectTo = '/dashboard', divider = 'or' }: { redirectTo?: string; divider?: string }) {
  const { loginWithGoogle } = useAuth()
  const navigate = useNavigate()
  const box = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const providers = useQuery({
    queryKey: ['auth-providers'],
    queryFn: async () => (await api.get<{ google_client_id: string | null }>('/auth/providers')).data,
    staleTime: Infinity,
    retry: false,
  })
  const clientId = providers.data?.google_client_id ?? null

  useEffect(() => {
    if (!clientId || !box.current) return
    let cancelled = false
    loadGsi()
      .then(() => {
        if (cancelled || !box.current || !window.google) return
        window.google.accounts.id.initialize({
          client_id: clientId,
          ux_mode: 'popup',
          callback: async ({ credential }) => {
            setError(null)
            setBusy(true)
            try {
              const user = await loginWithGoogle(credential)
              const target =
                redirectTo !== '/dashboard' ? redirectTo
                  : user.role === 'admin' ? '/admin'
                  : user.role === 'business' ? '/business'
                  : redirectTo
              navigate(target, { replace: true })
            } catch (err) {
              setError(apiErrorMessage(err, 'Google sign-in failed. Please try again.'))
            } finally {
              setBusy(false)
            }
          },
        })
        window.google.accounts.id.renderButton(box.current, {
          type: 'standard', theme: 'outline', size: 'large', text: 'continue_with', shape: 'pill',
          width: Math.min(400, box.current.clientWidth || 320),
        })
      })
      .catch(() => !cancelled && setError('Could not load Google sign-in. Check your connection.'))
    return () => {
      cancelled = true
    }
  }, [clientId, loginWithGoogle, navigate, redirectTo])

  const orLine = (
    <div className="flex items-center gap-3 text-xs uppercase tracking-wider text-slate-400">
      <span className="h-px flex-1 bg-slate-200" />
      {divider}
      <span className="h-px flex-1 bg-slate-200" />
    </div>
  )

  // Not set up on this server yet (no GOOGLE_CLIENT_ID): show the option,
  // switched off, rather than a gap where people expect it.
  if (!clientId) {
    if (providers.isPending) return <div className="h-[92px]" aria-hidden />
    return (
      <div className="space-y-4">
        <div className="space-y-1.5">
          <button
            type="button"
            disabled
            title="Google sign-in isn't switched on yet"
            className="flex h-11 w-full cursor-not-allowed items-center justify-center gap-3 rounded-full border border-slate-300 bg-white text-sm font-medium text-slate-400"
          >
            <GoogleG className="h-[18px] w-[18px] opacity-50" />
            Continue with Google
          </button>
          <p className="text-center text-xs text-slate-400">Google sign-in isn’t available yet — use your email below.</p>
        </div>
        {orLine}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div ref={box} className={`flex min-h-[44px] justify-center ${busy ? 'pointer-events-none opacity-60' : ''}`} />
      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-center text-sm text-red-700">{error}</p>}
      <div className="flex items-center gap-3 text-xs uppercase tracking-wider text-slate-400">
        <span className="h-px flex-1 bg-slate-200" />
        {divider}
        <span className="h-px flex-1 bg-slate-200" />
      </div>
    </div>
  )
}

/** Google's "G" mark, for the switched-off button (the live one is drawn by Google). */
function GoogleG({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={className} aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.6 5.4 2.7 13.3l7.9 6.1C12.5 13.5 17.8 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.1 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.4c-.5 2.9-2.2 5.3-4.6 6.9l7.4 5.7c4.3-4 6.9-9.9 6.9-17.1z" />
      <path fill="#FBBC05" d="M10.6 28.6c-.5-1.4-.8-3-.8-4.6s.3-3.2.8-4.6l-7.9-6.1C1 16.6 0 20.2 0 24s1 7.4 2.7 10.7l7.9-6.1z" />
      <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.4-5.7c-2.1 1.4-4.8 2.2-8.5 2.2-6.2 0-11.5-4-13.4-9.6l-7.9 6.1C6.6 42.6 14.6 48 24 48z" />
    </svg>
  )
}
