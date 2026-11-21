import { useState } from 'react'
import { api } from '@/lib/api'
import { apiErrorMessage, useAuth } from '@/lib/auth'

/** Download the plan as a PDF, or have it emailed. */
export function ExportBar({ tripId }: { tripId: string }) {
  const { user } = useAuth()
  const [downloading, setDownloading] = useState(false)
  const [emailState, setEmailState] = useState<'idle' | 'sending' | 'sent'>('idle')
  const [message, setMessage] = useState<string | null>(null)

  async function downloadPdf() {
    setDownloading(true)
    setMessage(null)
    try {
      // Fetched with the auth header, then saved -- a plain link cannot carry
      // the in-memory token.
      const response = await api.get<Blob>(`/trips/${tripId}/pdf`, { responseType: 'blob' })
      const disposition = String(response.headers['content-disposition'] ?? '')
      const name = /filename="([^"]+)"/.exec(disposition)?.[1] ?? 'itinerary.pdf'
      const url = URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = name
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setMessage(apiErrorMessage(err, 'Could not create the PDF.'))
    } finally {
      setDownloading(false)
    }
  }

  async function emailMe() {
    setEmailState('sending')
    setMessage(null)
    try {
      const { data } = await api.post<{ detail: string }>(`/trips/${tripId}/email`)
      setEmailState('sent')
      setMessage(data.detail)
    } catch (err) {
      setEmailState('idle')
      setMessage(apiErrorMessage(err, 'Could not send the email.'))
    }
  }

  const verified = Boolean(user?.is_verified)

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        onClick={downloadPdf}
        disabled={downloading}
        className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
      >
        {downloading ? 'Preparing…' : 'Download PDF'}
      </button>
      <button
        onClick={emailMe}
        disabled={!verified || emailState !== 'idle'}
        title={verified ? undefined : 'Confirm your email address first'}
        className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
      >
        {emailState === 'sending' ? 'Sending…' : emailState === 'sent' ? 'Sent' : 'Email me this'}
      </button>
      {!verified && (
        <span className="text-xs text-slate-500">Confirm your email to use “Email me this”.</span>
      )}
      {message && <span className="text-sm text-slate-600">{message}</span>}
    </div>
  )
}
