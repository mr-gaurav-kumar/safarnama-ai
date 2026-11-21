import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { tripKeys } from '@/features/trips/api'
import type { FeedbackSummary, Invitation, Match, Member, StyleTag } from '@/features/trips/types'

const keys = {
  members: (id: string) => ['trips', id, 'members'] as const,
  matches: (id: string) => ['trips', id, 'matches'] as const,
  feedback: (id: string) => ['trips', id, 'feedback'] as const,
  invitations: ['invitations'] as const,
}

export function useMembers(tripId: string) {
  return useQuery({
    queryKey: keys.members(tripId),
    queryFn: async () => (await api.get<Member[]>(`/trips/${tripId}/members`)).data,
  })
}

export function useInvitations() {
  return useQuery({
    queryKey: keys.invitations,
    queryFn: async () => (await api.get<Invitation[]>('/invitations')).data,
  })
}

export function useMatches(tripId: string, enabled: boolean) {
  return useQuery({
    queryKey: keys.matches(tripId),
    queryFn: async () => (await api.get<Match[]>(`/trips/${tripId}/matches`)).data,
    enabled,
  })
}

export function useFeedback(tripId: string) {
  return useQuery({
    queryKey: keys.feedback(tripId),
    queryFn: async () => (await api.get<FeedbackSummary>(`/trips/${tripId}/feedback`)).data,
  })
}

/** Everything that changes who is on a trip or what they want refreshes the
 *  same set of queries. */
function useInvalidateTrip(tripId: string) {
  const qc = useQueryClient()
  return () => {
    void qc.invalidateQueries({ queryKey: keys.members(tripId) })
    void qc.invalidateQueries({ queryKey: tripKeys.detail(tripId) })
    void qc.invalidateQueries({ queryKey: tripKeys.all })
    void qc.invalidateQueries({ queryKey: keys.invitations })
    void qc.invalidateQueries({ queryKey: keys.matches(tripId) })
  }
}

export function useInvite(tripId: string) {
  const done = useInvalidateTrip(tripId)
  return useMutation({
    mutationFn: async (email: string) =>
      (await api.post<{ detail: string }>(`/trips/${tripId}/invite`, { email })).data,
    onSuccess: done,
  })
}

export function useJoin(tripId: string) {
  const done = useInvalidateTrip(tripId)
  return useMutation({
    mutationFn: async (token?: string | null) =>
      (await api.post(`/trips/${tripId}/join`, token ? { token } : {})).data,
    onSuccess: done,
  })
}

export function useDecline(tripId: string) {
  const done = useInvalidateTrip(tripId)
  return useMutation({
    mutationFn: async (token?: string | null) => {
      await api.post(`/trips/${tripId}/decline`, token ? { token } : {})
    },
    onSuccess: done,
  })
}

export function useLeave(tripId: string) {
  const done = useInvalidateTrip(tripId)
  return useMutation({
    mutationFn: async () => {
      await api.post(`/trips/${tripId}/leave`)
    },
    onSuccess: done,
  })
}

export function useRemoveMember(tripId: string) {
  const done = useInvalidateTrip(tripId)
  return useMutation({
    mutationFn: async (memberId: string) => {
      await api.delete(`/trips/${tripId}/members/${memberId}`)
    },
    onSuccess: done,
  })
}

export function useSetPreferences(tripId: string) {
  const done = useInvalidateTrip(tripId)
  return useMutation({
    mutationFn: async (style_tags: StyleTag[]) => {
      await api.put(`/trips/${tripId}/my-preferences`, { style_tags })
    },
    onSuccess: done,
  })
}

export function useReplan(tripId: string) {
  const done = useInvalidateTrip(tripId)
  return useMutation({
    mutationFn: async () => (await api.post(`/trips/${tripId}/replan`)).data,
    onSuccess: done,
  })
}

export function useSetDiscoverable(tripId: string) {
  const done = useInvalidateTrip(tripId)
  return useMutation({
    mutationFn: async (discoverable: boolean) =>
      (await api.put(`/trips/${tripId}/discoverable`, { discoverable })).data,
    onSuccess: done,
  })
}

export function useRequestMatch(tripId: string) {
  const done = useInvalidateTrip(tripId)
  return useMutation({
    mutationFn: async (otherId: string) =>
      (await api.post<{ detail: string }>(`/trips/${tripId}/matches/${otherId}/request`)).data,
    onSuccess: done,
  })
}

export function useRate(tripId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: { rating: number; comment?: string }) =>
      (await api.put<FeedbackSummary>(`/trips/${tripId}/feedback`, body)).data,
    onSuccess: (data) => {
      qc.setQueryData(keys.feedback(tripId), data)
      void qc.invalidateQueries({ queryKey: tripKeys.all })
    },
  })
}
