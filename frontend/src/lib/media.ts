/** Uploaded files are served by the backend at /media/...; in the browser
 *  that goes through the /api proxy. External https:// links pass through. */
export function mediaUrl(url: string): string {
  return url.startsWith('/media/') ? `/api${url}` : url
}

/** A calm fallback cover when a package has no photo yet -- one of a few
 *  deep tones, picked from the title so it stays the same everywhere. */
const COVERS = [
  'from-slate-900 via-indigo-950 to-slate-900',
  'from-emerald-950 via-slate-900 to-slate-950',
  'from-sky-950 via-slate-900 to-indigo-950',
  'from-stone-900 via-amber-950 to-slate-950',
  'from-rose-950 via-slate-900 to-slate-950',
]
export function coverTone(seed: string): string {
  let h = 0
  for (const c of seed) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return COVERS[h % COVERS.length]
}
