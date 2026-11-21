import { formatWhen, useDeleteFeedback, useFeedback } from './api'
import {
  ConfirmButton, ErrorNote, PageHeader, Pagination, TableCard, Td, Th, usePaged,
} from './ui'
import type { AdminFeedback } from './types'

/** Filled stars up to the rating, hollow after -- readable at a glance in a
 *  column of fifty rows, which a bare number is not. */
function Stars({ rating }: { rating: number }) {
  const tone = rating <= 2 ? 'text-red-600' : rating === 3 ? 'text-amber-600' : 'text-emerald-600'
  return (
    <span className={`whitespace-nowrap ${tone}`} title={`${rating} out of 5`}>
      <span aria-hidden="true">{'★'.repeat(rating)}{'☆'.repeat(5 - rating)}</span>
      <span className="sr-only">{rating} out of 5</span>
    </span>
  )
}

export function FeedbackPage() {
  const paged = usePaged(25)
  const { data, isPending, isError } = useFeedback(paged.limit, paged.offset)

  const rated = data?.items ?? []
  const average = rated.length
    ? (rated.reduce((sum, f) => sum + f.rating, 0) / rated.length).toFixed(1)
    : null

  return (
    <>
      <PageHeader
        title="Feedback"
        subtitle={
          average
            ? `Average ${average} out of 5 on this page. Ratings feed back into each traveller's memory.`
            : 'Ratings feed back into each traveller’s memory.'
        }
      />

      <TableCard
        colSpan={5}
        isPending={isPending}
        isError={isError}
        isEmpty={rated.length === 0}
        emptyText="No feedback yet."
        head={
          <tr>
            <Th className="w-28">Rating</Th>
            <Th>Trip</Th>
            <Th>Comment</Th>
            <Th>When</Th>
            <Th className="text-right">Actions</Th>
          </tr>
        }
        footer={<Pagination total={data?.total ?? 0} paged={paged} />}
      >
        {rated.map((f) => <FeedbackRow key={f.id} feedback={f} />)}
      </TableCard>
    </>
  )
}

function FeedbackRow({ feedback }: { feedback: AdminFeedback }) {
  const remove = useDeleteFeedback()

  return (
    <tr className={feedback.rating <= 2 ? 'bg-red-50/50' : undefined}>
      <Td><Stars rating={feedback.rating} /></Td>
      <Td>
        <span className="block font-medium">{feedback.destination}</span>
        <span className="block text-xs text-slate-500">{feedback.user_email}</span>
      </Td>
      <Td className="max-w-md text-slate-700">
        {feedback.comment || <span className="text-slate-400">No comment</span>}
      </Td>
      <Td className="text-xs text-slate-500">{formatWhen(feedback.created_at)}</Td>
      <Td className="text-right">
        <ConfirmButton
          disabled={remove.isPending}
          confirmLabel="Delete"
          onConfirm={() => remove.mutate(feedback.id)}
        >
          Delete
        </ConfirmButton>
        <ErrorNote error={remove.error} fallback="Could not delete that." />
      </Td>
    </tr>
  )
}
