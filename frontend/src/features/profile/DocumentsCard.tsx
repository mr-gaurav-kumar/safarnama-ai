import { useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { apiErrorMessage } from '@/lib/auth'
import { Icon } from '@/components/Icon'
import { OCR_KINDS, PdfPasswordNeeded, readDocument, type OcrKind } from '@/features/profile/ocr'

type Kind = 'aadhaar' | 'pan' | 'driving_licence' | 'passport' | 'voter_id' | 'other'

interface Doc {
  id: string
  kind: Kind
  title: string
  number_masked: string | null
  expires_on: string | null
  days_left: number | null
  has_file: boolean
  file_type: string | null
  file_size: number | null
  updated_at: string
}

const SLOTS: { kind: Kind; title: string; hint: string; placeholder: string; expires: boolean }[] = [
  { kind: 'aadhaar', title: 'Aadhaar', hint: '12 digits', placeholder: '2345 6789 0123', expires: false },
  { kind: 'pan', title: 'PAN card', hint: 'Like ABCDE1234F', placeholder: 'ABCDE1234F', expires: false },
  { kind: 'driving_licence', title: 'Driving licence', hint: 'Like DL0420191234567', placeholder: 'DL04 20191234567', expires: true },
  { kind: 'passport', title: 'Passport', hint: 'One letter and 7 digits', placeholder: 'K1234567', expires: true },
]
const EXTRA: { kind: Kind; title: string; placeholder: string; expires: boolean }[] = [
  { kind: 'voter_id', title: 'Voter ID', placeholder: 'ABC1234567', expires: false },
  { kind: 'other', title: 'Other document', placeholder: 'Number (optional)', expires: true },
]

const key = ['my-documents']

function useDocs() {
  return useQuery({
    queryKey: key,
    queryFn: async () => (await api.get<{ enabled: boolean; items: Doc[] }>('/me/documents')).data,
  })
}

/**
 * "My documents" on the profile: Aadhaar, PAN, driving licence, passport and
 * more, stored encrypted so you have them on any trip. Numbers stay masked
 * until you choose to show them; files open only for you.
 */
export function DocumentsCard() {
  const docs = useDocs()
  const [adding, setAdding] = useState<Kind | null>(null)
  const [extra, setExtra] = useState<Kind>('voter_id')

  if (docs.isPending) return null
  const items = docs.data?.items ?? []
  const byKind = (k: Kind) => items.find((d) => d.kind === k)
  const others = items.filter((d) => d.kind === 'other' || d.kind === 'voter_id')

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 px-6 py-5 sm:px-8">
        <div>
          <h2 className="text-lg font-semibold">My documents</h2>
          <p className="mt-0.5 max-w-xl text-sm text-slate-500">
            Keep a copy of your IDs with you on every trip. Stored encrypted — only you can see them, not even our team.
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800">
          <Icon name="lock" className="h-3.5 w-3.5" /> Encrypted
        </span>
      </div>

      <div className="space-y-5 px-6 py-6 sm:px-8">
        {docs.data && !docs.data.enabled ? (
          <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Document storage isn’t switched on yet. The site owner needs to set DOCUMENT_ENCRYPTION_KEY.
          </p>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              {SLOTS.map((s) => {
                const d = byKind(s.kind)
                if (adding === s.kind) {
                  return <DocForm key={s.kind} kind={s.kind} title={s.title} placeholder={s.placeholder} expires={s.expires} onDone={() => setAdding(null)} />
                }
                return d ? (
                  <DocTile key={s.kind} d={d} placeholder={s.placeholder} expires={s.expires} />
                ) : (
                  <button
                    key={s.kind}
                    onClick={() => setAdding(s.kind)}
                    className="flex min-h-[132px] flex-col items-start justify-between rounded-2xl border border-dashed border-slate-300 p-5 text-left transition hover:border-[#1C2452]/50 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-[#1C2452]"
                  >
                    <span>
                      <span className="block font-medium text-slate-900">{s.title}</span>
                      <span className="text-sm text-slate-500">{s.hint}</span>
                    </span>
                    <span className="inline-flex items-center gap-1.5 text-sm font-medium text-[#1C2452]">
                      <Icon name="plus" className="h-4 w-4" /> Add
                    </span>
                  </button>
                )
              })}
              {others.map((d) => {
                const meta = EXTRA.find((e) => e.kind === d.kind)!
                return <DocTile key={d.id} d={d} placeholder={meta.placeholder} expires={meta.expires} />
              })}
            </div>

            {adding && !SLOTS.some((s) => s.kind === adding) ? (
              <DocForm
                kind={adding}
                title={EXTRA.find((e) => e.kind === adding)!.title}
                placeholder={EXTRA.find((e) => e.kind === adding)!.placeholder}
                expires={EXTRA.find((e) => e.kind === adding)!.expires}
                withLabel={adding === 'other'}
                onDone={() => setAdding(null)}
              />
            ) : (
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-slate-500">Add another:</span>
                <select
                  value={extra}
                  onChange={(e) => setExtra(e.target.value as Kind)}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5"
                >
                  {EXTRA.filter((e) => e.kind === 'other' || !byKind(e.kind)).map((e) => (
                    <option key={e.kind} value={e.kind}>{e.title}</option>
                  ))}
                </select>
                <button onClick={() => setAdding(extra)} className="rounded-lg border border-slate-200 px-3 py-1.5 font-medium text-slate-700 hover:bg-slate-50">
                  Add
                </button>
              </div>
            )}

            <p className="rounded-xl bg-slate-50 px-4 py-3 text-xs leading-relaxed text-slate-600">
              A saved copy is handy for bookings and check-ins, but some places — airports especially — only accept the
              original or DigiLocker. For Aadhaar, the masked version from UIDAI is safer to share.
            </p>
          </>
        )}
      </div>
    </section>
  )
}

function DocTile({ d, placeholder, expires }: { d: Doc; placeholder: string; expires: boolean }) {
  const qc = useQueryClient()
  const [number, setNumber] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const del = useMutation({
    mutationFn: async () => api.delete(`/me/documents/${d.id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  })

  async function reveal() {
    if (number) return setNumber(null)
    try {
      const { data } = await api.get<{ number: string | null }>(`/me/documents/${d.id}/number`)
      setNumber(data.number)
      setTimeout(() => setNumber(null), 30_000) // hide again after 30 s
    } catch (e) {
      setErr(apiErrorMessage(e, 'Could not show the number.'))
    }
  }

  async function openFile() {
    setErr(null)
    // Opened in a new tab first (synchronously, so pop-up blockers allow it),
    // then pointed at the decrypted file once it has arrived.
    const tab = window.open('', '_blank')
    try {
      const res = await api.get<Blob>(`/me/documents/${d.id}/file`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      if (tab) tab.location.href = url
      else window.location.href = url
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (e) {
      tab?.close()
      setErr(apiErrorMessage(e, 'Could not open the file.'))
    }
  }

  if (editing) {
    return <DocForm kind={d.kind} title={d.title} placeholder={placeholder} expires={expires} existing={d} onDone={() => setEditing(false)} />
  }

  const expiry = d.days_left
  const expiryNote =
    expiry === null ? null
      : expiry < 0 ? { text: 'Expired', cls: 'bg-red-50 text-red-800' }
      : expiry <= 180 ? { text: `Expires in ${expiry} days`, cls: 'bg-amber-50 text-amber-900' }
      : { text: `Valid till ${new Date(`${d.expires_on}T00:00:00`).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}`, cls: 'bg-slate-100 text-slate-600' }

  return (
    <article className="flex min-h-[132px] flex-col justify-between gap-3 rounded-2xl bg-[#1C2452] p-5 text-white">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-medium">{d.title}</p>
          {d.number_masked ? (
            <p className="mt-1 font-mono text-[15px] tracking-wider text-white/85">{number ?? d.number_masked}</p>
          ) : (
            <p className="mt-1 text-sm text-white/50">No number saved</p>
          )}
        </div>
        {expiryNote && <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${expiryNote.cls}`}>{expiryNote.text}</span>}
      </div>

      <div className="flex flex-wrap items-center gap-1.5 text-sm">
        {d.number_masked && (
          <button onClick={reveal} className="inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-2.5 py-1.5 hover:bg-white/20">
            <Icon name={number ? 'eyeOff' : 'eye'} className="h-4 w-4" /> {number ? 'Hide' : 'Show'}
          </button>
        )}
        {d.has_file && (
          <button onClick={openFile} className="inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-2.5 py-1.5 hover:bg-white/20">
            <Icon name="file" className="h-4 w-4" /> View
          </button>
        )}
        <button onClick={() => setEditing(true)} className="rounded-lg px-2.5 py-1.5 text-white/70 hover:text-white">Edit</button>
        {confirming ? (
          <span className="ml-auto inline-flex gap-1">
            <button onClick={() => del.mutate()} disabled={del.isPending} className="rounded-lg bg-red-500 px-2.5 py-1.5 font-medium hover:bg-red-600">
              Delete
            </button>
            <button onClick={() => setConfirming(false)} className="rounded-lg px-2.5 py-1.5 text-white/70">Cancel</button>
          </span>
        ) : (
          <button onClick={() => setConfirming(true)} className="ml-auto rounded-lg px-2.5 py-1.5 text-white/50 hover:text-red-300" aria-label={`Delete ${d.title}`}>
            Remove
          </button>
        )}
      </div>
      {err && <p className="text-xs text-red-300">{err}</p>}
    </article>
  )
}

function DocForm({
  kind, title, placeholder, expires, existing, withLabel, onDone,
}: {
  kind: Kind; title: string; placeholder: string; expires: boolean; existing?: Doc; withLabel?: boolean; onDone: () => void
}) {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [number, setNumber] = useState('')
  const [expiresOn, setExpiresOn] = useState(existing?.expires_on ?? '')
  const [label, setLabel] = useState(existing?.kind === 'other' ? existing.title : '')
  const [fileName, setFileName] = useState<string | null>(null)

  // Reading the number off the photo / PDF -- on this device, see ocr.ts.
  type Ocr = 'idle' | 'reading' | 'found' | 'notfound' | 'masked' | 'password' | 'error'
  const [ocr, setOcr] = useState<Ocr>('idle')
  const [progress, setProgress] = useState(0)
  const [found, setFound] = useState<string | null>(null)
  const [pdfPassword, setPdfPassword] = useState('')
  const [wrongPassword, setWrongPassword] = useState(false)
  const canRead = (OCR_KINDS as string[]).includes(kind)

  async function read(file: File, password?: string) {
    setOcr('reading')
    setProgress(0)
    try {
      const r = await readDocument(file, kind as OcrKind, { password, onProgress: setProgress })
      if (r.masked) return setOcr('masked')
      if (!r.number) return setOcr('notfound')
      setFound(r.number)
      setNumber((cur) => (cur.trim() ? cur : r.number!))
      if (expires && r.expires_on) setExpiresOn((cur) => cur || r.expires_on!)
      setOcr('found')
    } catch (e) {
      if (e instanceof PdfPasswordNeeded) {
        setWrongPassword(e.wrong)
        return setOcr('password')
      }
      setOcr('error')
    }
  }

  const save = useMutation({
    mutationFn: async () => {
      const form = new FormData()
      if (!existing) form.append('kind', kind)
      if (number.trim()) form.append('number', number.trim())
      if (expires && expiresOn) form.append('expires_on', expiresOn)
      if (withLabel && label.trim()) form.append('label', label.trim())
      const f = fileRef.current?.files?.[0]
      if (f) form.append('file', f)
      // Same as the package photo upload: the API client defaults to JSON,
      // and axios would turn a FormData into JSON without this.
      const cfg = { headers: { 'Content-Type': 'multipart/form-data' } }
      return existing
        ? (await api.put<Doc>(`/me/documents/${existing.id}`, form, cfg)).data
        : (await api.post<Doc>('/me/documents', form, cfg)).data
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: key })
      onDone()
    },
  })

  function submit(e: FormEvent) {
    e.preventDefault()
    save.mutate()
  }

  const field = 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-900'
  return (
    <form onSubmit={submit} className="space-y-3 rounded-2xl border border-slate-300 bg-slate-50 p-5 sm:col-span-2">
      <p className="font-medium text-slate-900">{existing ? `Update ${title}` : `Add ${title}`}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        {withLabel && (
          <label className="space-y-1 text-sm sm:col-span-2">
            <span className="text-slate-600">What is it?</span>
            <input className={field} value={label} onChange={(e) => setLabel(e.target.value)} maxLength={60} placeholder="e.g. Student ID, Visa" required />
          </label>
        )}
        <label className="space-y-1 text-sm">
          <span className="text-slate-600">{existing?.number_masked ? 'New number (leave empty to keep)' : 'Number'}</span>
          <input
            className={`${field} font-mono`}
            value={number}
            onChange={(e) => setNumber(e.target.value)}
            placeholder={placeholder}
            autoComplete="off"
            spellCheck={false}
            maxLength={30}
          />
        </label>
        {expires && (
          <label className="space-y-1 text-sm">
            <span className="text-slate-600">Valid till (optional)</span>
            <input className={field} type="date" value={expiresOn} onChange={(e) => setExpiresOn(e.target.value)} />
          </label>
        )}
        <div className="space-y-1 text-sm sm:col-span-2">
          <span className="text-slate-600">{existing?.has_file ? 'Replace the photo or PDF (optional)' : 'Photo or PDF (optional, up to 5 MB)'}</span>
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" onClick={() => fileRef.current?.click()} className="rounded-lg border border-slate-300 bg-white px-3 py-2 font-medium text-slate-700 hover:bg-slate-100">
              Choose file
            </button>
            <span className="truncate text-slate-500">{fileName ?? 'No file chosen'}</span>
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,application/pdf"
              className="sr-only"
              onChange={(e) => {
                const f = e.target.files?.[0]
                setFileName(f?.name ?? null)
                setOcr('idle')
                if (f && canRead) void read(f)
              }}
            />
          </div>
          {canRead && ocr === 'idle' && (
            <p className="text-xs text-slate-500">Add a photo or PDF and we’ll read the number for you — on this device, nothing is sent anywhere to read it.</p>
          )}
          {ocr === 'reading' && (
            <p className="flex items-center gap-2 text-xs text-slate-600">
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-300 border-t-[#1C2452]" />
              Reading the number from your {fileName?.toLowerCase().endsWith('.pdf') ? 'PDF' : 'photo'}…{progress > 0 ? ` ${Math.round(progress * 100)}%` : ''}
            </p>
          )}
          {ocr === 'found' && (
            <p className="text-xs text-emerald-700">
              ✓ Read <span className="font-mono font-semibold">{found}</span> from the file. Check it matches your card before saving.
              {number.trim() && found && number.replace(/\s/g, '').toUpperCase() !== found && (
                <button type="button" onClick={() => setNumber(found)} className="ml-1 font-medium underline">Use it</button>
              )}
            </p>
          )}
          {ocr === 'notfound' && <p className="text-xs text-amber-700">Couldn’t read the number clearly — please type it in.</p>}
          {ocr === 'masked' && (
            <p className="text-xs text-amber-700">This is a masked Aadhaar: only the last 4 digits are printed. Type the full number if you want it saved.</p>
          )}
          {ocr === 'error' && <p className="text-xs text-amber-700">Couldn’t read this file — you can still save it and type the number.</p>}
          {ocr === 'password' && (
            <div className="mt-1 space-y-1.5 rounded-lg bg-white p-3 ring-1 ring-slate-200">
              <p className="text-xs text-slate-700">
                {wrongPassword ? 'That password didn’t open it. ' : 'This PDF is locked. '}
                {kind === 'aadhaar'
                  ? 'An e-Aadhaar password is the first 4 letters of your name in capitals and your birth year, e.g. RAJA1990.'
                  : 'Enter its password to read the number.'}{' '}
                The password is only used here, never saved or sent.
              </p>
              <div className="flex gap-2">
                <input
                  type="password"
                  value={pdfPassword}
                  onChange={(e) => setPdfPassword(e.target.value)}
                  className="w-48 rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
                  autoComplete="off"
                />
                <button
                  type="button"
                  onClick={() => { const f = fileRef.current?.files?.[0]; if (f) void read(f, pdfPassword) }}
                  className="rounded-lg bg-[#1C2452] px-3 py-1.5 text-sm font-medium text-white"
                >
                  Read
                </button>
                <button type="button" onClick={() => setOcr('idle')} className="text-xs text-slate-500">Skip</button>
              </div>
            </div>
          )}
        </div>
      </div>
      {save.isError && <p className="text-sm text-red-600">{apiErrorMessage(save.error, 'Could not save the document.')}</p>}
      <div className="flex gap-2">
        <button type="submit" disabled={save.isPending} className="rounded-lg bg-[#1C2452] px-4 py-2 text-sm font-semibold text-white hover:bg-[#283372] disabled:opacity-50">
          {save.isPending ? 'Saving…' : 'Save'}
        </button>
        <button type="button" onClick={onDone} className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:text-slate-900">Cancel</button>
      </div>
    </form>
  )
}
