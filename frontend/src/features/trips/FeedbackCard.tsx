import { useEffect, useState } from 'react'
import { apiErrorMessage } from '@/lib/auth'
import { useFeedback, useRate } from '@/features/trips/groupApi'

/** After the trip: 1-5 stars and a note. The organiser's rating steers what the
 *  planner draws on next time. */
export function FeedbackCard({ tripId, isOwner }: { tripId: string; isOwner: boolean }) {
  const { data } = useFeedback(tripId)
  const rate = useRate(tripId)
  const [stars, setStars] = useState(0)
  const [comment, setComment] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (data?.mine) {
      setStars(data.mine.rating)
      setComment(data.mine.comment ?? '')
    }
  }, [data?.mine?.rating, data?.mine?.comment]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!data?.can_rate) return null

  async function save() {
    setError(null)
    try {
      await rate.mutateAsync({ rating: stars, comment: comment.trim() || undefined })
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not save your rating.'))
    }
  }

  const saved = data.mine && data.mine.rating === stars && (data.mine.comment ?? '') === comment

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-medium">How was the trip?</h2>
      <p className="text-sm text-slate-600">
        {isOwner
          ? 'Your rating shapes future plans: trips you loved count for more, and the planner steers away from what you didn’t enjoy.'
          : 'Let the organiser know how it went.'}
      </p>

      <div className="mt-3 flex items-center gap-1" role="radiogroup" aria-label="Rating">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            role="radio"
            aria-checked={stars === n}
            aria-label={`${n} star${n > 1 ? 's' : ''}`}
            onClick={() => setStars(n)}
            className={`text-2xl leading-none ${n <= stars ? 'text-amber-500' : 'text-slate-300'} hover:text-amber-400`}
          >
            ★
          </button>
        ))}
        {data.count > 0 && (
          <span className="ml-3 text-sm text-slate-500">
            {data.count} rating{data.count > 1 ? 's' : ''} · average {data.average}
          </span>
        )}
      </div>

      <label className="mt-3 block text-sm">
        <span className="sr-only">Comment</span>
        <textarea
          rows={2}
          maxLength={1000}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="What stood out? What would you skip next time?"
          className="w-full rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-900"
        />
      </label>

      <div className="mt-2 flex items-center gap-3">
        <button
          onClick={save}
          disabled={stars === 0 || rate.isPending || Boolean(saved)}
          className="rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40"
        >
          {saved ? 'Saved' : rate.isPending ? 'Saving…' : 'Save rating'}
        </button>
        {error && <span className="text-sm text-red-700">{error}</span>}
      </div>
    </section>
  )
}
