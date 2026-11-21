import { useState } from 'react'
import { mediaUrl } from '@/lib/media'

/**
 * A person's picture, or their initials when they haven't added one (or it
 * fails to load). Used everywhere a person is shown, so a new photo shows up
 * in the navbar, the profile and the admin lists at once.
 */
export function Avatar({
  name, url, className = 'h-9 w-9 text-sm', tone = 'bg-slate-100 text-slate-700',
}: {
  name?: string | null
  url?: string | null
  className?: string
  tone?: string
}) {
  const [broken, setBroken] = useState<string | null>(null)
  const initials = (name ?? '?')
    .trim()
    .split(/\s+/)
    .map((p) => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase() || '?'

  if (url && broken !== url) {
    return (
      <img
        src={mediaUrl(url)}
        alt={name ? `${name}’s profile picture` : 'Profile picture'}
        onError={() => setBroken(url)}
        className={`shrink-0 rounded-full object-cover ${className}`}
      />
    )
  }
  return (
    <span aria-hidden className={`flex shrink-0 items-center justify-center rounded-full font-semibold ${tone} ${className}`}>
      {initials}
    </span>
  )
}
