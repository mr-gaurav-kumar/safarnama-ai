export const STYLE_TAGS = ['adventure', 'relax', 'culture', 'food', 'nature'] as const
export type StyleTag = (typeof STYLE_TAGS)[number]

export type TripStatus = 'processing' | 'completed' | 'failed'
export type PlanStatus = 'draft' | 'saved' | 'upcoming' | 'completed'

export interface ItineraryItem {
  time: string
  place: string
  activity: string
  estimated_cost: number
  /** Present when the place could be located for the map. */
  lat?: number
  lng?: number
}

export interface ItineraryDay {
  day: number
  date: string
  items: ItineraryItem[]
}

export interface MemorySource {
  trip_id: string
  destination: string
  start_date: string
  similarity: number
}

export type SeasonLabel = 'ideal' | 'pleasant' | 'hot' | 'rainy' | 'cold'

/** "Think on the Plan" -- what the planner weighed before writing (Phase 8). */
export interface Thinking {
  version: number
  place: {
    name: string
    state: string
    /** matched: we know it; nearby/state: read like a neighbour */
    how: 'matched' | 'nearby' | 'state'
    region: string
    region_name: string
  } | null
  headline: string
  seasons: { month: number; label: SeasonLabel; confidence: number }[]
  crowd: 'busy' | 'average' | 'quiet'
  budget: {
    per_person_per_day: number
    on_ground_per_day: number
    typical: number | null
    verdict: 'tight' | 'workable' | 'comfortable' | 'generous' | null
  }
  style: { strong: string[]; weak: string[] }
  thoughts: string[]
  prompt_notes: string[]
  model: string
}

export interface Itinerary {
  day_plan: ItineraryDay[]
  budget_breakdown: Record<string, number>
  explanation: string | null
  /** Past trips retrieval fed into this plan, best match first. */
  memory_sources: MemorySource[] | null
  /** Null for plans made before Phase 8. */
  thinking?: Thinking | null
}

export interface Trip {
  id: string
  destination: string
  start_date: string
  end_date: string
  budget: string
  travelers: number
  style_tags: string[]
  use_memory: boolean
  status: TripStatus
  plan_status: PlanStatus
  error: string | null
  created_at: string
  discoverable: boolean
  /** ai: made by the planner; manual: written by the traveller; copy: planned again. */
  source: 'ai' | 'manual' | 'copy'
  role: 'owner' | 'member'
  member_count: number
  my_rating: number | null
}

export interface Member {
  id: string | null
  name: string | null
  email: string
  role: 'owner' | 'member' | 'invited' | 'declined'
  style_tags: string[]
  is_you: boolean
}

export interface Invitation {
  trip_id: string
  destination: string
  start_date: string
  end_date: string
  invited_by: string
}

export interface Match {
  trip_id: string
  first_name: string
  start_date: string
  end_date: string
  overlap_days: number
  already_requested: boolean
}

export interface FeedbackSummary {
  can_rate: boolean
  mine: { rating: number; comment: string | null } | null
  count: number
  average: number | null
}

export interface TripDetail extends Trip {
  itinerary: Itinerary | null
}

export interface TripCreate {
  destination: string
  start_date: string
  end_date: string
  budget: number
  travelers: number
  style_tags: StyleTag[]
  use_memory: boolean
}
