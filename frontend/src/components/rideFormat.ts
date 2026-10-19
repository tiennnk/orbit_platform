import type { Ride } from '../api/client'

export const STATUS_LABELS: Record<Ride['status'], string> = {
  searching: 'Finding a driver',
  no_driver: 'No driver found',
  assigned: 'Driver on the way',
  in_progress: 'On trip',
  completed: 'Completed',
  cancelled: 'Cancelled',
}

const vnd = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' })

export function formatFare(amount: number): string {
  return vnd.format(amount)
}

export function formatRating(average: number | null, count: number): string {
  if (average === null || count === 0) {
    return 'New driver'
  }
  return `${average.toFixed(1)} / 5 from ${count} ${count === 1 ? 'rating' : 'ratings'}`
}
