import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { PackageBooking, TravelPackage } from '@/features/admin/types'

export type { PackageBooking, TravelPackage }

export function usePackages() {
  return useQuery({
    queryKey: ['packages'],
    queryFn: async () => (await api.get<TravelPackage[]>('/packages')).data,
  })
}

export function usePackage(id: string | undefined) {
  return useQuery({
    queryKey: ['packages', id],
    queryFn: async () => (await api.get<TravelPackage>(`/packages/${id}`)).data,
    enabled: !!id,
  })
}

export function useMyBookings(enabled: boolean) {
  return useQuery({
    queryKey: ['packages', 'mine'],
    queryFn: async () => (await api.get<PackageBooking[]>('/packages/bookings/mine')).data,
    enabled,
  })
}

export function useBookPackage(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: { travelers: number; start_date: string; note?: string }) =>
      (await api.post<PackageBooking>(`/packages/${id}/book`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['packages'] }),
  })
}

export function useCancelBooking() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => (await api.post<PackageBooking>(`/packages/bookings/${id}/cancel`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['packages'] }),
  })
}

export const INR = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

export function fmtDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}
