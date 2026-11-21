import { useRef, useState } from 'react'
import { api } from '@/lib/api'
import { apiErrorMessage, useAuth, type AuthUser } from '@/lib/auth'
import { Avatar } from '@/components/Avatar'
import { Icon } from '@/components/Icon'

const MAX_MB = 5

/** The profile picture on the profile page, with change and remove. */
export function AvatarEditor() {
  const { user, updateUser } = useAuth()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (!user) return null

  async function upload(file: File) {
    setError(null)
    if (file.size > MAX_MB * 1024 * 1024) return setError(`Photos must be under ${MAX_MB} MB.`)
    const form = new FormData()
    form.append('file', file)
    setBusy(true)
    try {
      const { data } = await api.post<AuthUser>('/auth/me/avatar', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      updateUser(data)
    } catch (e) {
      setError(apiErrorMessage(e, 'Could not upload that photo.'))
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }

  async function remove() {
    setError(null)
    setBusy(true)
    try {
      updateUser((await api.delete<AuthUser>('/auth/me/avatar')).data)
    } catch (e) {
      setError(apiErrorMessage(e, 'Could not remove the photo.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        onClick={() => input.current?.click()}
        disabled={busy}
        className="group relative rounded-full focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#1C2452]"
        aria-label={user.avatar_url ? 'Change profile picture' : 'Add a profile picture'}
      >
        <Avatar name={user.name} url={user.avatar_url} className="h-24 w-24 text-2xl" tone="bg-[#1C2452] text-white" />
        <span
          className={`absolute inset-0 flex items-center justify-center rounded-full bg-black/45 text-white transition ${
            busy ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100'
          }`}
        >
          {busy ? (
            <span className="h-6 w-6 animate-spin rounded-full border-2 border-white/40 border-t-white" />
          ) : (
            <Icon name="plus" className="h-6 w-6" />
          )}
        </span>
      </button>
      <div className="flex items-center gap-3 text-xs">
        <button type="button" onClick={() => input.current?.click()} disabled={busy} className="font-medium text-[#1C2452] hover:underline">
          {user.avatar_url ? 'Change photo' : 'Add photo'}
        </button>
        {user.avatar_url && (
          <button type="button" onClick={remove} disabled={busy} className="text-slate-500 hover:text-red-600">
            Remove
          </button>
        )}
      </div>
      {error && <p className="max-w-[12rem] text-center text-xs text-red-600">{error}</p>}
      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) void upload(f)
        }}
      />
    </div>
  )
}
