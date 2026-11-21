/** Mirrors backend/app/schemas/admin.py. Keep the two in step. */

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface Stats {
  users_total: number
  users_blocked: number
  signups_7d: number
  trips_total: number
  trips_active: number
  trips_processing: number
  open_fraud_flags: number
  open_escalations: number
  packages_active: number
  bookings_pending: number
  businesses_pending: number
}

export type Role = 'user' | 'admin' | 'business'

export interface AdminUser {
  id: string
  name: string
  email: string
  role: Role
  is_verified: boolean
  is_blocked: boolean
  created_at: string
  trip_count: number
  open_flags: number
  home_town?: string | null
  avatar_url?: string | null
}

export interface AdminTripDetail {
  id: string
  destination: string
  start_date: string
  end_date: string
  status: string
  plan_status: string
  budget: number
  travelers: number
  style_tags: string[]
  created_at: string
}

export interface AdminUserDetail extends AdminUser {
  updated_at: string
  date_of_birth: string | null
  phone: string | null
  gender: string | null
  travel_interests: string[] | null
  trips: AdminTripDetail[]
  last_login_at: string | null
  login_count: number
}

export interface UserCreate {
  name: string
  email: string
  password: string
  is_verified: boolean
  home_town?: string
  phone?: string
}

export interface UserUpdate {
  name?: string
  email?: string
  password?: string
  is_blocked?: boolean
  is_verified?: boolean
  home_town?: string
  phone?: string
  date_of_birth?: string
  gender?: 'male' | 'female' | 'other' | 'prefer_not'
}

export type TripStatus = 'processing' | 'completed' | 'failed'
export type PlanStatus = 'draft' | 'saved' | 'upcoming' | 'completed'

export interface AdminTrip {
  id: string
  destination: string
  start_date: string
  end_date: string
  status: string
  plan_status: string
  owner_email: string
  member_count: number
  created_at: string
  error: string | null
  budget: number
  travelers: number
  style_tags: string[]
}

export interface TripUpdate {
  status?: TripStatus
  plan_status?: PlanStatus
  destination?: string
  start_date?: string
  end_date?: string
  budget?: number
  travelers?: number
  style_tags?: string[]
}

export interface TripCreateAdmin {
  destination: string
  start_date: string
  end_date: string
  budget: number
  travelers: number
  style_tags: string[]
  use_memory: boolean
}

export interface TravelPackage {
  id: string
  title: string
  destination: string
  duration_days: number
  price_per_person: number
  summary: string
  description: string
  inclusions: string[]
  highlights: string[]
  style_tags: string[]
  images: string[]
  seats: number | null
  seats_left: number | null
  valid_from: string | null
  valid_until: string | null
  is_active: boolean
  created_at: string
  booking_count: number
  business_name: string | null
  business_slug: string | null
}

export type PackageInput = Omit<
  TravelPackage,
  'id' | 'seats_left' | 'created_at' | 'booking_count' | 'business_name' | 'business_slug'
>

export interface Business {
  user_id: string
  business_name: string
  slug: string
  kind: string
  city: string
  business_phone: string
  description: string
  website: string | null
  gst_number: string | null
  status: 'pending' | 'approved' | 'rejected' | 'suspended'
  status_reason: string | null
  created_at: string
  reviewed_at: string | null
  owner_name: string | null
  owner_email: string | null
  package_count: number
  bookings_pending: number
  /** The owner's login is blocked -- nothing of theirs is shown to anyone. */
  owner_blocked: boolean
  /** Approved and not blocked: travellers can see its packages. */
  is_visible: boolean
}

export type BusinessKind = 'agency' | 'tour_operator' | 'hotel' | 'other'

/** The editable profile of a business (PUT /admin/businesses/:id/profile). */
export interface BusinessFields {
  business_name: string
  kind: BusinessKind
  city: string
  business_phone: string
  description: string
  website: string | null
  gst_number: string | null
}

/** POST /admin/businesses: the owner's login plus the business. */
export interface BusinessCreate extends BusinessFields {
  owner_name: string
  owner_email: string
  password: string
  is_verified: boolean
  status: Business['status']
}

export type BookingStatus = 'pending' | 'confirmed' | 'cancelled'

export interface PackageBooking {
  id: string
  package_id: string
  package_title: string
  destination: string
  duration_days: number
  travelers: number
  start_date: string
  end_date: string
  total_price: number
  note: string | null
  status: BookingStatus
  created_at: string
  user_name: string | null
  user_email: string | null
}

export type FlagStatus = 'open' | 'resolved' | 'dismissed'

export interface AdminFlag {
  id: string
  user_id: string
  user_email: string
  user_blocked: boolean
  trip_id: string | null
  reason: string
  risk_score: number
  details: Record<string, unknown>
  status: string
  created_at: string
  reviewed_at: string | null
}

export interface FlagUpdate {
  status: FlagStatus
  block_user: boolean
}

export type EscalationStatus = 'open' | 'resolved'

export interface AdminEscalation {
  id: string
  user_email: string
  reason: string
  intent: string | null
  excerpt: string
  status: string
  created_at: string
}

export interface AdminFeedback {
  id: string
  trip_id: string
  destination: string
  user_email: string
  rating: number
  comment: string | null
  created_at: string
}

export interface AdminChatLine {
  id: string
  user_email: string
  sender: string
  message: string
  intent: string | null
  sentiment: string | null
  created_at: string
}

export interface AuditLine {
  id: string
  admin_email: string | null
  action: string
  target_type: string
  target_id: string
  details: Record<string, unknown>
  created_at: string
}
