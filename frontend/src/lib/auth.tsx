import { clearSavedChats } from '@/lib/savedChat'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  api,
  refreshSession,
  setAccessToken,
  setRefreshHandler,
  setUnauthorizedHandler,
  type SessionUser,
} from '@/lib/api'

export type Role = 'user' | 'admin' | 'business'

export type AuthUser = SessionUser

export interface BusinessSignup {
  name: string
  email: string
  password: string
  phone?: string
  business_name: string
  kind: 'agency' | 'tour_operator' | 'hotel' | 'other'
  city: string
  business_phone: string
  description?: string
  website?: string
  gst_number?: string
}

export interface SignupProfile {
  date_of_birth?: string
  home_town?: string
  phone?: string
  gender?: 'male' | 'female' | 'other' | 'prefer_not'
  travel_interests?: string[]
}

interface TokenResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

interface AuthState {
  user: AuthUser | null
  isAuthenticated: boolean
  isAdmin: boolean
  isBusiness: boolean
  /** True until the first session check finishes, so guards do not bounce
   *  a logged-in user to /login during a page reload. */
  isLoading: boolean
  /** Resolves with the signed-in user, so a caller can branch on role. */
  login: (email: string, password: string) => Promise<AuthUser>
  /** Sign in (or up) with the ID token Google Identity Services handed us. */
  loginWithGoogle: (credential: string) => Promise<AuthUser>
  signup: (name: string, email: string, password: string, profile?: SignupProfile) => Promise<AuthUser>
  /** Register an agency / business account (pending admin approval). */
  signupBusiness: (body: BusinessSignup) => Promise<AuthUser>
  logout: () => Promise<void>
  /** Replace the cached user, e.g. after the email is verified. */
  updateUser: (user: AuthUser) => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Local-only: the session could not be renewed.
  const dropSession = useCallback(() => {
    setAccessToken(null)
    setUser(null)
  }, [])

  const logout = useCallback(async () => {
    try {
      // Revokes the refresh cookie on the server, so a reload stays logged out.
      await api.post('/auth/logout')
    } catch {
      // Logging out locally matters more than the server hearing about it.
    }
    clearSavedChats()
    dropSession()
  }, [dropSession])

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await api.post<TokenResponse>('/auth/login', { email, password })
    setAccessToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const loginWithGoogle = useCallback(async (credential: string) => {
    const { data } = await api.post<TokenResponse>('/auth/google', { credential })
    setAccessToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const signup = useCallback(async (name: string, email: string, password: string, profile: SignupProfile = {}) => {
    const { data } = await api.post<TokenResponse>('/auth/signup', {
      name,
      email,
      password,
      ...profile,
    })
    setAccessToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const signupBusiness = useCallback(async (body: BusinessSignup) => {
    const { data } = await api.post<TokenResponse>('/auth/signup-business', body)
    setAccessToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  // A 401 that a refresh could not fix drops the session here, in one place.
  useEffect(() => {
    setUnauthorizedHandler(dropSession)
    setRefreshHandler((next) => setUser(next))
    return () => {
      setUnauthorizedHandler(null)
      setRefreshHandler(null)
    }
  }, [dropSession])

  // A page load starts with no access token (it lives in memory). The refresh
  // cookie, if there is one, restores the session before any guard decides.
  useEffect(() => {
    let cancelled = false
    refreshSession().finally(() => {
      if (!cancelled) setIsLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const updateUser = useCallback((next: AuthUser) => {
    // Only if it is the same account -- a link opened while logged in as
    // someone else must not swap the session.
    setUser((current) => (current && current.id === next.id ? next : current))
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isAdmin: user?.role === 'admin',
      isBusiness: user?.role === 'business',
      isLoading,
      login,
      loginWithGoogle,
      signup,
      signupBusiness,
      logout,
      updateUser,
    }),
    [user, isLoading, login, loginWithGoogle, signup, signupBusiness, logout, updateUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

/** Turns an axios error into the message the API actually sent. */
export function apiErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data
    ?.detail
  if (typeof detail === 'string') return detail
  // FastAPI validation errors come back as a list of objects.
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string }
    if (typeof first?.msg === 'string') return first.msg
  }
  return fallback
}
