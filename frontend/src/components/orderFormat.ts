import type { Order } from '../api/client'

export type OrderStage =
  | 'placed'
  | 'rejected'
  | 'cancelled'
  | 'finding_driver'
  | 'no_driver'
  | 'driver_to_restaurant'
  | 'on_the_way'
  | 'delivered'

export function orderStage(order: Order): OrderStage {
  if (order.status !== 'accepted') {
    return order.status
  }
  switch (order.delivery?.status) {
    case 'assigned':
      return 'driver_to_restaurant'
    case 'in_progress':
      return 'on_the_way'
    case 'completed':
      return 'delivered'
    case 'no_driver':
    case 'cancelled':
      return 'no_driver'
    default:
      return 'finding_driver'
  }
}

export const STAGE_LABELS: Record<OrderStage, string> = {
  placed: 'Waiting for the restaurant',
  rejected: 'Rejected by the restaurant',
  cancelled: 'Cancelled',
  finding_driver: 'Preparing, finding a driver',
  no_driver: 'Preparing, no driver yet',
  driver_to_restaurant: 'Driver heading to the restaurant',
  on_the_way: 'On the way to you',
  delivered: 'Delivered',
}

export const STAGE_BADGES: Record<OrderStage, string> = {
  placed: 'badge-pending',
  rejected: 'badge-rejected',
  cancelled: 'badge-cancelled',
  finding_driver: 'badge-pending',
  no_driver: 'badge-no_driver',
  driver_to_restaurant: 'badge-assigned',
  on_the_way: 'badge-in_progress',
  delivered: 'badge-completed',
}

export function isOrderOpen(order: Order): boolean {
  return !['rejected', 'cancelled', 'delivered'].includes(orderStage(order))
}
