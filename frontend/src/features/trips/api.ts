import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Trip, TripCreate, TripDetail } from '@/features/trips/types'

export const tripKeys = {
  all: ['trips'] as const,
  detail: (id: string) => ['trips', id] as const,
}

export function useTrips() {
  return useQuery({
    queryKey: tripKeys.all,
    queryFn: async () => (await api.get<Trip[]>('/trips')).data,
  })
}

export function useTrip(id: string | undefined) {
  return useQuery({
    queryKey: tripKeys.detail(id ?? ''),
    queryFn: async () => (await api.get<TripDetail>(`/trips/${id}`)).data,
    enabled: Boolean(id),
    // While the plan is being made, check now and then even if the live
    // connection is down -- the page must never get stuck on a spinner.
    refetchInterval: (query) => (query.state.data?.status === 'processing' ? 4000 : false),
  })
}

export function useCreateTrip() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: TripCreate) =>
      (await api.post<TripDetail>('/trips', payload)).data,
    onSuccess: (trip) => {
      qc.setQueryData(tripKeys.detail(trip.id), trip)
      void qc.invalidateQueries({ queryKey: tripKeys.all })
    },
  })
}

export function useDeleteTrip() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/trips/${id}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: tripKeys.all }),
  })
}

export interface PlanItemInput {
  time: string
  activity: string
  place: string
  estimated_cost: number
}
export interface PackItemInput {
  name: string
  category: string
  quantity: number
}
export interface PlanDayInput {
  items: PlanItemInput[]
}
export interface OwnPlanCreate {
  destination: string
  start_date: string
  end_date: string
  budget: number
  travelers: number
  style_tags: string[]
  notes: string | null
  days: PlanDayInput[]
  packing: PackItemInput[]
}

function saved(qc: ReturnType<typeof useQueryClient>, trip: TripDetail) {
  qc.setQueryData(tripKeys.detail(trip.id), trip)
  void qc.invalidateQueries({ queryKey: tripKeys.all })
}

/** A plan the traveller wrote: saved and ready at once, no AI. */
export function useCreateOwnPlan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: OwnPlanCreate) => (await api.post<TripDetail>('/trips/own', payload)).data,
    onSuccess: (trip) => saved(qc, trip),
  })
}

export interface FillResult {
  days: { items: PlanItemInput[] }[]
  packing: PackItemInput[]
  /** ai: Gemini wrote the suggestions; rules: the app's own lists did. */
  source: 'ai' | 'rules'
  added_items: number
  filled_fields: number
}

/** Fill the gaps in a plan being written. Nothing is saved; your own entries come back unchanged. */
export function useFillPlan() {
  return useMutation({
    mutationFn: async (payload: OwnPlanCreate) => (await api.post<FillResult>('/trips/own/fill', payload)).data,
  })
}

/** Replace the days of a plan you own -- yours or the AI's. */
export function useEditPlan(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { days: PlanDayInput[]; notes: string | null; packing?: PackItemInput[] }) =>
      (await api.put<TripDetail>(`/trips/${id}/plan`, payload)).data,
    onSuccess: (trip) => {
      saved(qc, trip)
      void qc.invalidateQueries({ queryKey: ['packing', trip.id] })
    },
  })
}

/** The same trip again on new dates, as a new trip of yours. */
export function useCopyTrip() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, start_date }: { id: string; start_date: string }) =>
      (await api.post<TripDetail>(`/trips/${id}/copy`, { start_date })).data,
    onSuccess: (trip) => saved(qc, trip),
  })
}

/** Rupees, no decimals -- costs here are never to the paisa. */
export function formatINR(value: number | string): string {
  const n = typeof value === 'string' ? Number(value) : value
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number.isFinite(n) ? n : 0)
}

export function formatDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}
