import type { Ride } from '../api/client'

export const STATUS_LABELS: Record<Ride['status'], string> = {
  assigned: 'Driver on the way',
  in_progress: 'On trip',
  completed: 'Completed',
  cancelled: 'Cancelled',
}

const vnd = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' })

export function formatFare(amount: number): string {
  return vnd.format(amount)
}
