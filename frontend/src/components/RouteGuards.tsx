import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/lib/auth'

function Checking() {
  return <p className="text-sm text-slate-500">Checking your session…</p>
}

/**
 * Convenience only. The real check is server-side on every request --
 * a frontend guard keeps the UI honest, it does not secure anything.
 */
export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) return <Checking />
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  return <Outlet />
}

/**
 * The admin area has its own door: someone who is not signed in lands on
 * /admin/login, not the traveller login, and a signed-in traveller is sent
 * back to their own dashboard rather than shown an empty admin shell.
 */
export function AdminRoute() {
  const { isAuthenticated, isAdmin, isLoading } = useAuth()

  if (isLoading) return <Checking />
  if (!isAuthenticated) return <Navigate to="/admin/login" replace />
  if (!isAdmin) return <Navigate to="/dashboard" replace />
  return <Outlet />
}

/** The partner dashboard: business accounts only. */
export function BusinessRoute() {
  const { isAuthenticated, isBusiness, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) return <Checking />
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (!isBusiness) return <Navigate to="/dashboard" replace />
  return <Outlet />
}
