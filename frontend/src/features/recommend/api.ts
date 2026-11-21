import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { SeasonLabel, StyleTag } from '@/features/trips/types'

export interface BudgetRequest {
  budget: number
  days: number
  travelers: number
  month: number | null
  style_tags: StyleTag[]
  use_memory: boolean
  limit?: number
  /** Where the trip starts -- prices every place from here. */
  origin?: string
  /** Optional: a place (and what's near it) or a state. */
  destination?: string | null
}

export interface Recommendation {
  name: string
  state: string
  blurb: string
  score: number
  style_match: number
  /** on-ground money per person per day ÷ the place's typical cost */
  budget_fit: number
  daily_cost: number
  season: SeasonLabel | null
  season_confidence: number | null
  styles: Record<StyleTag, number>
  reasons: string[]
  visited: boolean
  distance_km?: number | null
  travel_mode?: string | null
  /** per person, there and back */
  travel_fare?: number | null
  estimate?: { total: number; verdict: 'comfortable' | 'fits' | 'tight' | 'over' | null; travel: number; stay: number; food: number; local: number } | null
  is_destination?: boolean
}

export interface BudgetResponse {
  per_person_per_day: number
  on_ground_per_day: number
  travel_share: number
  considered: number
  over_budget: number
  closed: number
  taste: string[]
  items: Recommendation[]
  note: string
  origin?: string | null
  origin_found?: boolean
  destination_mode?: 'place' | 'state' | 'not_found' | null
  destination_note?: string | null
}

export function useBudgetRecommendations() {
  return useMutation({
    mutationFn: async (body: BudgetRequest) =>
      (await api.post<BudgetResponse>('/recommend/budget', body)).data,
  })
}
