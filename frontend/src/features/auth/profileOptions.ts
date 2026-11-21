import type { IconName } from '@/components/Icon'
import type { SignupProfile } from '@/lib/auth'

export const MIN_AGE = 13

export const GENDERS: { value: NonNullable<SignupProfile['gender']>; label: string }[] = [
  { value: 'female', label: 'Female' },
  { value: 'male', label: 'Male' },
  { value: 'other', label: 'Other' },
  { value: 'prefer_not', label: 'Prefer not to say' },
]

export const INTERESTS: { value: string; label: string; icon: IconName }[] = [
  { value: 'adventure', label: 'Adventure', icon: 'mountain' },
  { value: 'relax', label: 'Relaxation', icon: 'sun' },
  { value: 'culture', label: 'Culture & heritage', icon: 'landmark' },
  { value: 'food', label: 'Food', icon: 'coffee' },
  { value: 'nature', label: 'Nature', icon: 'leaf' },
  { value: 'spiritual', label: 'Spiritual', icon: 'star' },
  { value: 'shopping', label: 'Shopping', icon: 'bag' },
  { value: 'nightlife', label: 'Nightlife', icon: 'moon' },
]

export function isoYearsAgo(years: number): string {
  const d = new Date()
  d.setFullYear(d.getFullYear() - years)
  return d.toISOString().slice(0, 10)
}

export function ageOf(dob: string): number {
  const b = new Date(`${dob}T00:00:00`)
  const t = new Date()
  let a = t.getFullYear() - b.getFullYear()
  if (t.getMonth() < b.getMonth() || (t.getMonth() === b.getMonth() && t.getDate() < b.getDate())) a--
  return a
}
