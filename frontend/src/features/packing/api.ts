/** Packing list API: one hook per endpoint in backend/app/routers/packing.py. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export type Category = 'clothes' | 'footwear' | 'toiletries' | 'documents' | 'electronics' | 'health' | 'accessories' | 'other'

export const CATEGORIES: { key: Category; label: string; emoji: string }[] = [
  { key: 'clothes', label: 'Clothes', emoji: '👕' },
  { key: 'footwear', label: 'Footwear', emoji: '👟' },
  { key: 'toiletries', label: 'Toiletries', emoji: '🧴' },
  { key: 'documents', label: 'Documents & money', emoji: '🪪' },
  { key: 'electronics', label: 'Electronics', emoji: '🔌' },
  { key: 'health', label: 'Health', emoji: '🩹' },
  { key: 'accessories', label: 'Accessories', emoji: '🎒' },
  { key: 'other', label: 'Other', emoji: '📦' },
]

export interface PackingItem {
  id: string
  name: string
  category: Category
  quantity: number
  packed_going: boolean
  packed_return: boolean
  source: 'mine' | 'ai' | 'admin'
  /** Added by the admin: can be ticked, not changed or removed. */
  locked: boolean
  note: string | null
}

export interface PackingList {
  trip_id: string
  destination: string
  start_date: string
  end_date: string
  items: PackingItem[]
  progress: { total: number; packed_going: number; packed_return: number }
}

export interface Suggestion {
  name: string
  category: Category
  quantity: number
  reason: string
}

export interface Suggestions {
  items: Suggestion[]
  source: 'ai' | 'rules'
  context: string[]
}

export interface NewItem {
  name: string
  category: Category
  quantity: number
}

const key = (tripId: string) => ['packing', tripId] as const

export function usePackingList(tripId: string) {
  return useQuery({
    queryKey: key(tripId),
    queryFn: async () => (await api.get<PackingList>(`/trips/${tripId}/packing`)).data,
  })
}

/** Every change returns the whole list, so the cache is simply replaced. */
function useListMutation<A>(tripId: string, fn: (a: A) => Promise<PackingList>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (list) => {
      qc.setQueryData(key(tripId), list)
      void qc.invalidateQueries({ queryKey: ['packing-suggestions', tripId] })
    },
  })
}

export function useAddItem(tripId: string) {
  return useListMutation(tripId, async (item: NewItem) => (await api.post<PackingList>(`/trips/${tripId}/packing`, item)).data)
}

export function useAddMany(tripId: string) {
  return useListMutation(tripId, async (items: NewItem[]) =>
    (await api.post<PackingList>(`/trips/${tripId}/packing/bulk`, { items, source: 'ai' })).data)
}

export function useUpdateItem(tripId: string) {
  return useListMutation(
    tripId,
    async ({ id, ...change }: { id: string; quantity?: number; packed_going?: boolean; packed_return?: boolean }) =>
      (await api.patch<PackingList>(`/trips/${tripId}/packing/${id}`, change)).data,
  )
}

export function useDeleteItem(tripId: string) {
  return useListMutation(tripId, async (id: string) => (await api.delete<PackingList>(`/trips/${tripId}/packing/${id}`)).data)
}

export function useResetTicks(tripId: string) {
  return useListMutation(tripId, async (which: 'going' | 'return') =>
    (await api.post<PackingList>(`/trips/${tripId}/packing/reset/${which}`)).data)
}

export function useSuggestions(tripId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['packing-suggestions', tripId],
    queryFn: async () => (await api.get<Suggestions>(`/trips/${tripId}/packing/suggestions`)).data,
    enabled,
    staleTime: 5 * 60_000,
  })
}

// --- admin -------------------------------------------------------------------

export interface PackingDefault {
  id: string
  name: string
  category: Category
  quantity: number
  note: string | null
  user_id: string | null
  user_email: string | null
  user_name: string | null
  created_at: string
}

export function useDefaults() {
  return useQuery({
    queryKey: ['admin', 'packing-defaults'],
    queryFn: async () => (await api.get<PackingDefault[]>('/admin/packing-defaults')).data,
  })
}

function useAdminMutation<A, R>(fn: (a: A) => Promise<R>) {
  const qc = useQueryClient()
  return useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: ['admin'] }) })
}

export function useCreateDefault() {
  return useAdminMutation(async (body: NewItem & { note?: string; user_email?: string }) =>
    (await api.post<PackingDefault>('/admin/packing-defaults', body)).data)
}

export function useUpdateDefault() {
  return useAdminMutation(async ({ id, ...body }: NewItem & { id: string; note?: string | null }) =>
    (await api.put<PackingDefault>(`/admin/packing-defaults/${id}`, body)).data)
}

export function useDeleteDefault() {
  return useAdminMutation(async (id: string) => {
    await api.delete(`/admin/packing-defaults/${id}`)
  })
}
