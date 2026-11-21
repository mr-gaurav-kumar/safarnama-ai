/**
 * The admin API client. One hook per endpoint in backend/app/routers/admin.py.
 *
 * Every mutation invalidates `['admin']`, so a block, a resolve or a delete
 * refreshes the stat tiles in the sidebar as well as the table it happened in --
 * the counts an admin acts on are never stale.
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type {
  AdminChatLine, AdminEscalation, AdminFeedback, AdminFlag, AdminTrip, AdminUser, AdminUserDetail,
  AuditLine, BookingStatus, EscalationStatus, FlagUpdate, PackageBooking, PackageInput, Page, Stats,
  TravelPackage, TripCreateAdmin, TripUpdate, UserCreate, UserUpdate, Business, BusinessCreate, BusinessFields,
} from './types'

/** Drops empty strings and undefined so `?q=` never reaches the API. */
function params(obj: Record<string, string | number | undefined>) {
  const out: Record<string, string | number> = {}
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined && v !== '') out[k] = v
  }
  return out
}

function useAdminMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin'] }),
  })
}

/* Every paged table passes `placeholderData: keepPreviousData` so the old page
   stays visible while the next one loads -- the layout does not jump on every
   keystroke. It is written out per query rather than spread from a shared
   object, because spreading loses the generic inference keepPreviousData needs. */

// --- stats -----------------------------------------------------------------

export function useStats() {
  return useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: async () => (await api.get<Stats>('/admin/stats')).data,
    refetchInterval: 60_000,
  })
}

// --- users -----------------------------------------------------------------

export function useUsers(q: string, limit: number, offset: number) {
  return useQuery({
    queryKey: ['admin', 'users', q, limit, offset],
    queryFn: async () =>
      (await api.get<Page<AdminUser>>('/admin/users', { params: params({ q, limit, offset }) })).data,
    placeholderData: keepPreviousData,
    staleTime: 10_000,
  })
}

export function useUserDetail(id: string | null) {
  return useQuery({
    queryKey: ['admin', 'user', id],
    queryFn: async () => (await api.get<AdminUserDetail>(`/admin/users/${id}`)).data,
    enabled: !!id,
  })
}

export function useCreateUser() {
  return useAdminMutation(async (payload: UserCreate) =>
    (await api.post<AdminUser>('/admin/users', payload)).data)
}

export function useUpdateUser() {
  return useAdminMutation(async ({ id, patch }: { id: string; patch: UserUpdate }) =>
    (await api.put<AdminUser>(`/admin/users/${id}`, patch)).data)
}

export function useDeleteUser() {
  return useAdminMutation(async (id: string) => {
    await api.delete(`/admin/users/${id}`)
  })
}

// --- trips -----------------------------------------------------------------

export function useAdminTrips(q: string, status: string, limit: number, offset: number) {
  return useQuery({
    queryKey: ['admin', 'trips', q, status, limit, offset],
    queryFn: async () =>
      (await api.get<Page<AdminTrip>>('/admin/trips', { params: params({ q, status, limit, offset }) })).data,
    placeholderData: keepPreviousData,
    staleTime: 10_000,
  })
}

export function useUpdateTrip() {
  return useAdminMutation(async ({ id, patch }: { id: string; patch: TripUpdate }) =>
    (await api.put<AdminTrip>(`/admin/trips/${id}`, patch)).data)
}

export function useDeleteTrip() {
  return useAdminMutation(async (id: string) => {
    await api.delete(`/admin/trips/${id}`)
  })
}

export function useCreateTripForUser() {
  return useAdminMutation(async ({ userId, payload }: { userId: string; payload: TripCreateAdmin }) =>
    (await api.post<AdminTrip>(`/admin/users/${userId}/trips`, payload)).data)
}

export function useReplanTrip() {
  return useAdminMutation(async (id: string) => (await api.post<AdminTrip>(`/admin/trips/${id}/replan`)).data)
}

// --- packages --------------------------------------------------------------

export function useAdminPackages() {
  return useQuery({
    queryKey: ['admin', 'packages'],
    queryFn: async () => (await api.get<TravelPackage[]>('/admin/packages')).data,
  })
}

export function useSavePackage() {
  return useAdminMutation(async ({ id, payload }: { id?: string; payload: PackageInput }) =>
    id
      ? (await api.put<TravelPackage>(`/admin/packages/${id}`, payload)).data
      : (await api.post<TravelPackage>('/admin/packages', payload)).data)
}

export function useDeletePackage() {
  return useAdminMutation(async (id: string) => {
    await api.delete(`/admin/packages/${id}`)
  })
}

export function useAdminBookings(status: string, limit: number, offset: number) {
  return useQuery({
    queryKey: ['admin', 'bookings', status, limit, offset],
    queryFn: async () =>
      (await api.get<Page<PackageBooking>>('/admin/package-bookings', { params: params({ status, limit, offset }) })).data,
    placeholderData: keepPreviousData,
    staleTime: 10_000,
  })
}

export function useUpdateBooking() {
  return useAdminMutation(async ({ id, status }: { id: string; status: BookingStatus }) =>
    (await api.put<PackageBooking>(`/admin/package-bookings/${id}`, { status })).data)
}

export function useDeleteBooking() {
  return useAdminMutation(async (id: string) => {
    await api.delete(`/admin/package-bookings/${id}`)
  })
}

// --- businesses ------------------------------------------------------------

export function useBusinesses(status: string, q: string, limit: number, offset: number) {
  return useQuery({
    queryKey: ['admin', 'businesses', status, q, limit, offset],
    queryFn: async () =>
      (await api.get<Page<Business>>('/admin/businesses', { params: params({ status, q, limit, offset }) })).data,
    placeholderData: keepPreviousData,
    staleTime: 10_000,
  })
}

export function useCreateBusiness() {
  return useAdminMutation(async (body: BusinessCreate) =>
    (await api.post<Business>('/admin/businesses', body)).data)
}

export function useUpdateBusiness() {
  return useAdminMutation(async ({ id, body }: { id: string; body: BusinessFields }) =>
    (await api.put<Business>(`/admin/businesses/${id}/profile`, body)).data)
}

/** Block = owner signed out and locked out, and everything they publish hidden. */
export function useBlockBusiness() {
  return useAdminMutation(async ({ id, blocked, reason }: { id: string; blocked: boolean; reason?: string }) =>
    (await api.put<Business>(`/admin/businesses/${id}/block`, { blocked, reason })).data)
}

export function useSetBusinessStatus() {
  return useAdminMutation(async ({ id, status, reason }: { id: string; status: Business['status']; reason?: string }) =>
    (await api.put<Business>(`/admin/businesses/${id}`, { status, reason })).data)
}

// --- fraud flags -----------------------------------------------------------

export function useFlags(status: string, limit: number, offset: number) {
  return useQuery({
    queryKey: ['admin', 'flags', status, limit, offset],
    queryFn: async () =>
      (await api.get<Page<AdminFlag>>('/admin/fraud-flags', { params: params({ status, limit, offset }) })).data,
    placeholderData: keepPreviousData,
    staleTime: 10_000,
  })
}

export function useReviewFlag() {
  return useAdminMutation(async ({ id, patch }: { id: string; patch: FlagUpdate }) =>
    (await api.put<AdminFlag>(`/admin/fraud-flags/${id}`, patch)).data)
}

// --- support escalations ---------------------------------------------------

export function useEscalations(status: string, limit: number, offset: number) {
  return useQuery({
    queryKey: ['admin', 'escalations', status, limit, offset],
    queryFn: async () =>
      (await api.get<Page<AdminEscalation>>('/admin/escalations', { params: params({ status, limit, offset }) })).data,
    placeholderData: keepPreviousData,
    staleTime: 10_000,
  })
}

export function useUpdateEscalation() {
  return useAdminMutation(async ({ id, status }: { id: string; status: EscalationStatus }) =>
    (await api.put<AdminEscalation>(`/admin/escalations/${id}`, { status })).data)
}

// --- feedback --------------------------------------------------------------

export function useFeedback(limit: number, offset: number) {
  return useQuery({
    queryKey: ['admin', 'feedback', limit, offset],
    queryFn: async () =>
      (await api.get<Page<AdminFeedback>>('/admin/feedback', { params: params({ limit, offset }) })).data,
    placeholderData: keepPreviousData,
    staleTime: 10_000,
  })
}

export function useDeleteFeedback() {
  return useAdminMutation(async (id: string) => {
    await api.delete(`/admin/feedback/${id}`)
  })
}

// --- chat logs -------------------------------------------------------------

export function useChatLogs(q: string, userEmail: string, limit: number, offset: number) {
  return useQuery({
    queryKey: ['admin', 'chat-logs', q, userEmail, limit, offset],
    queryFn: async () =>
      (await api.get<Page<AdminChatLine>>('/admin/chat-logs', {
        params: params({ q, user_email: userEmail, limit, offset }),
      })).data,
    placeholderData: keepPreviousData,
    staleTime: 10_000,
  })
}

// --- audit -----------------------------------------------------------------

export function useAudit(limit: number, offset: number) {
  return useQuery({
    queryKey: ['admin', 'audit', limit, offset],
    queryFn: async () =>
      (await api.get<Page<AuditLine>>('/admin/audit', { params: params({ limit, offset }) })).data,
    placeholderData: keepPreviousData,
    staleTime: 10_000,
  })
}

// --- formatting ------------------------------------------------------------

const DATE_TIME = new Intl.DateTimeFormat('en-IN', {
  day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
})

export function formatWhen(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '--' : DATE_TIME.format(d)
}

const DATE_ONLY = new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })

export function formatDay(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '--' : DATE_ONLY.format(d)
}
