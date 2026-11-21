import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Business, BookingStatus, PackageBooking, PackageInput, Page, TravelPackage } from '@/features/admin/types'

export type { Business }

function useBizMutation<A, R>(fn: (a: A) => Promise<R>) {
  const qc = useQueryClient()
  return useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: ['business'] }) })
}

export function useMyBusiness() {
  return useQuery({
    queryKey: ['business', 'me'],
    queryFn: async () => (await api.get<Business>('/business/me')).data,
  })
}

export function useUpdateBusiness() {
  return useBizMutation(async (body: {
    business_name: string; kind: string; city: string; business_phone: string
    description: string; website?: string | null; gst_number?: string | null
  }) => (await api.put<Business>('/business/me', body)).data)
}

export function useBizPackages() {
  return useQuery({
    queryKey: ['business', 'packages'],
    queryFn: async () => (await api.get<TravelPackage[]>('/business/packages')).data,
  })
}

export function useSaveBizPackage() {
  return useBizMutation(async ({ id, payload }: { id?: string; payload: PackageInput }) =>
    id
      ? (await api.put<TravelPackage>(`/business/packages/${id}`, payload)).data
      : (await api.post<TravelPackage>('/business/packages', payload)).data)
}

export function useDeleteBizPackage() {
  return useBizMutation(async (id: string) => {
    await api.delete(`/business/packages/${id}`)
  })
}

export function useBizBookings(status: string) {
  return useQuery({
    queryKey: ['business', 'bookings', status],
    queryFn: async () =>
      (await api.get<Page<PackageBooking>>('/business/bookings', { params: status ? { status, limit: 100 } : { limit: 100 } })).data,
    placeholderData: keepPreviousData,
  })
}

export function useSetBizBooking() {
  return useBizMutation(async ({ id, status }: { id: string; status: BookingStatus }) =>
    (await api.put<PackageBooking>(`/business/bookings/${id}`, { status })).data)
}
