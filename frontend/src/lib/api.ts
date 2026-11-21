import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

// Two flags the response interceptor reads, typed on every request config.
declare module 'axios' {
  interface AxiosRequestConfig {
    /** Already retried once after a refresh -- do not loop. */
    _retried?: boolean
    /** Never try to refresh for this request (the refresh call itself). */
    _skipAuthRetry?: boolean
  }
}

/**
 * The single HTTP client. Nothing else in the app calls axios directly.
 *
 * Sessions work in two layers:
 *  - a short-lived ACCESS token, held in memory only (never localStorage), sent
 *    as a Bearer header;
 *  - a long-lived REFRESH token in an httpOnly cookie that no script can read.
 *    `refreshSession()` trades it for a new access token -- on page load, and
 *    whenever a request comes back 401.
 */
export const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  // Send the refresh cookie (needed once the API is on another origin).
  withCredentials: true,
})

/**
 * WebSocket address for a backend path such as "/ws/chat".
 *
 * In development the Vite proxy forwards /api (WebSockets included). In
 * production the frontend's host (Vercel) proxies plain HTTP but not
 * WebSockets, so VITE_WS_BASE points sockets straight at the backend, e.g.
 * wss://safarnama-api.onrender.com. Sockets authenticate with their first
 * message, not a cookie, so connecting across origins is fine.
 */
export function wsUrl(path: string): string {
  const base = import.meta.env.VITE_WS_BASE as string | undefined
  if (base) return `${base.replace(/\/$/, '')}${path}`
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${scheme}://${window.location.host}/api${path}`
}

let accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

// --- refreshing -----------------------------------------------------------------

export interface SessionUser {
  id: string
  name: string
  email: string
  role: 'user' | 'admin' | 'business'
  is_verified: boolean
  date_of_birth?: string | null
  home_town?: string | null
  phone?: string | null
  gender?: string | null
  travel_interests?: string[] | null
  /** /media/avatars/... or null for initials */
  avatar_url?: string | null
}

interface TokenResponse {
  access_token: string
  user: SessionUser
}

/** Told about every successful refresh, so the auth context stays in step. */
let onRefreshed: ((user: SessionUser) => void) | null = null
export function setRefreshHandler(fn: ((user: SessionUser) => void) | null): void {
  onRefreshed = fn
}

let inFlight: Promise<SessionUser | null> | null = null

/**
 * Exchange the refresh cookie for a new access token. Concurrent callers share
 * one request -- ten requests failing with 401 at once cause one refresh, not
 * ten (which would also trip the server's reuse detection).
 */
export function refreshSession(): Promise<SessionUser | null> {
  inFlight ??= api
    .post<TokenResponse>('/auth/refresh', null, {
      // The server refuses refresh without this header; a form on another
      // site cannot set it.
      headers: { 'X-Requested-With': 'fetch' },
      _skipAuthRetry: true,
    })
    .then(({ data }) => {
      setAccessToken(data.access_token)
      onRefreshed?.(data.user)
      return data.user
    })
    .catch(() => {
      setAccessToken(null)
      return null
    })
    .finally(() => {
      inFlight = null
    })
  return inFlight
}

// --- handling errors in one place ----------------------------------------------------

/** Set by the auth provider: the session is gone and could not be renewed. */
let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: (() => void) | null): void {
  onUnauthorized = fn
}

/** Set by the app shell so 429s surface as one toast instead of a silent failure. */
let onRateLimited: ((message: string) => void) | null = null
export function setRateLimitHandler(fn: ((message: string) => void) | null): void {
  onRateLimited = fn
}


// Credentials are wrong -- nothing to refresh.
const NO_REFRESH = ['/auth/login', '/auth/signup', '/auth/refresh', '/auth/logout']

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: string }>) => {
    const status = error.response?.status
    const config = error.config as InternalAxiosRequestConfig | undefined

    if (
      status === 401 &&
      config &&
      !config._retried &&
      !config._skipAuthRetry &&
      !NO_REFRESH.some((path) => config.url?.startsWith(path))
    ) {
      // The access token expired mid-session: renew it and try once more.
      config._retried = true
      const user = await refreshSession()
      if (user) {
        config.headers.Authorization = `Bearer ${getAccessToken()}`
        return api.request(config)
      }
      onUnauthorized?.()
    }

    if (status === 429) {
      onRateLimited?.(error.response?.data?.detail ?? 'Too many requests -- please slow down.')
    }

    return Promise.reject(error)
  },
)
