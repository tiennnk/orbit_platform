import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { ErrorText } from './ErrorText'

const SCORES = [1, 2, 3, 4, 5]
const SCORE_LABELS: Record<number, string> = {
  1: 'Very bad',
  2: 'Bad',
  3: 'Okay',
  4: 'Good',
  5: 'Excellent',
}

export function RatingForm({ rideId, driverName }: { rideId: number; driverName: string }) {
  const queryClient = useQueryClient()
  const [score, setScore] = useState<number | null>(null)
  const [comment, setComment] = useState('')

  const rate = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST('/api/v1/rides/{id}/rating/', {
          params: { path: { id: rideId } },
          body: { score: score!, comment },
        }),
      ),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['ride', rideId] }),
        queryClient.invalidateQueries({ queryKey: ['ride-history'] }),
      ]),
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    rate.mutate()
  }

  return (
    <form className="rating" onSubmit={submit}>
      <strong>How was your trip with {driverName}?</strong>
      <div className="row">
        {SCORES.map((value) => (
          <button
            key={value}
            type="button"
            className={score === value ? 'score' : 'score secondary'}
            aria-pressed={score === value}
            onClick={() => setScore(value)}
          >
            {value}
          </button>
        ))}
        <span className="muted">{score ? SCORE_LABELS[score] : 'Pick a score'}</span>
      </div>
      <label>
        Comment (optional)
        <textarea value={comment} onChange={(e) => setComment(e.target.value)} maxLength={500} rows={2} />
      </label>
      <ErrorText error={rate.error} />
      <div className="row">
        <button type="submit" disabled={score === null || rate.isPending}>
          Submit rating
        </button>
      </div>
    </form>
  )
}
