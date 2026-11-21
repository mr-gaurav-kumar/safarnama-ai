import { useRef, useState } from 'react'
import { api } from '@/lib/api'
import { apiErrorMessage } from '@/lib/auth'
import { mediaUrl } from '@/lib/media'
import { Icon } from '@/components/Icon'

const MAX = 10

/**
 * Photos for a package: upload from the computer (JPG/PNG/WebP, max 5 MB
 * each) or paste an https:// link. The first photo is the cover; any photo
 * can be made the cover, moved, or removed.
 */
export function ImageManager({ images, onChange }: { images: string[]; onChange: (next: string[]) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [link, setLink] = useState('')

  async function upload(files: FileList | null) {
    if (!files?.length) return
    setError(null)
    const room = MAX - images.length
    const list = Array.from(files).slice(0, room)
    if (files.length > room) setError(`Only ${MAX} photos per package — extra files were skipped.`)
    let next = [...images]
    setUploading(list.length)
    for (const file of list) {
      if (file.size > 5 * 1024 * 1024) {
        setError(`${file.name} is over 5 MB.`)
        setUploading((n) => n - 1)
        continue
      }
      const form = new FormData()
      form.append('file', file)
      try {
        const { data } = await api.post<{ url: string }>('/uploads/package-image', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        next = [...next, data.url]
        onChange(next)
      } catch (err) {
        setError(apiErrorMessage(err, `Could not upload ${file.name}.`))
      } finally {
        setUploading((n) => n - 1)
      }
    }
    if (input.current) input.current.value = ''
  }

  function addLink() {
    const url = link.trim()
    if (!url) return
    if (!/^https:\/\/\S+$/.test(url)) return setError('Paste a full https:// image link.')
    if (images.length >= MAX) return setError(`Only ${MAX} photos per package.`)
    onChange([...images, url])
    setLink('')
    setError(null)
  }

  const move = (i: number, to: number) => {
    const next = [...images]
    const [x] = next.splice(i, 1)
    next.splice(to, 0, x)
    onChange(next)
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-xs font-medium text-slate-600">Photos ({images.length}/{MAX}) — the first one is the cover</p>
        <p className="text-xs text-slate-400">JPG, PNG or WebP · up to 5 MB each</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {images.map((url, i) => (
          <figure key={url} className="group relative aspect-[4/3] overflow-hidden rounded-xl border border-slate-200 bg-slate-100">
            <img src={mediaUrl(url)} alt="" className="h-full w-full object-cover" loading="lazy" />
            {i === 0 && (
              <span className="absolute top-2 left-2 rounded-full bg-ink/85 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-gold uppercase">
                Cover
              </span>
            )}
            <div className="absolute inset-x-0 bottom-0 flex justify-between gap-1 bg-gradient-to-t from-black/70 to-transparent p-2 opacity-100 transition sm:opacity-0 sm:group-hover:opacity-100">
              <div className="flex gap-1">
                {i > 0 && (
                  <button type="button" title="Move left" onClick={() => move(i, i - 1)} className="rounded-md bg-white/90 p-1 text-slate-800">
                    <Icon name="back" className="h-3.5 w-3.5" />
                  </button>
                )}
                {i > 0 && (
                  <button type="button" onClick={() => move(i, 0)} className="rounded-md bg-white/90 px-2 py-1 text-[11px] font-medium text-slate-800">
                    Make cover
                  </button>
                )}
              </div>
              <button
                type="button"
                title="Remove"
                onClick={() => onChange(images.filter((_, j) => j !== i))}
                className="rounded-md bg-white/90 p-1 text-red-600"
              >
                <Icon name="close" className="h-3.5 w-3.5" />
              </button>
            </div>
          </figure>
        ))}

        {images.length < MAX && (
          <button
            type="button"
            onClick={() => input.current?.click()}
            disabled={uploading > 0}
            className="flex aspect-[4/3] flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed border-slate-300 text-sm text-slate-500 transition hover:border-slate-400 hover:bg-slate-50 disabled:opacity-60"
          >
            {uploading > 0 ? (
              <>
                <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-slate-600" />
                Uploading {uploading}…
              </>
            ) : (
              <>
                <Icon name="plus" className="h-5 w-5" />
                Add photos
              </>
            )}
          </button>
        )}
      </div>

      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        hidden
        onChange={(e) => upload(e.target.files)}
      />

      <div className="flex gap-2">
        <input
          value={link}
          onChange={(e) => setLink(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              addLink()
            }
          }}
          placeholder="…or paste an image link (https://)"
          className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-900"
        />
        <button type="button" onClick={addLink} className="rounded-lg border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50">
          Add link
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}
