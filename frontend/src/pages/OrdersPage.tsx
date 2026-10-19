import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { ErrorText } from '../components/ErrorText'
import { STAGE_BADGES, STAGE_LABELS, isOrderOpen, orderStage } from '../components/orderFormat'
import { formatFare } from '../components/rideFormat'

const PAGE_SIZE = 10
const dateTime = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export function OrdersPage() {
  const [page, setPage] = useState(1)

  const orders = useQuery({
    queryKey: ['my-orders', page],
    queryFn: () => unwrap(api.GET('/api/v1/food/orders/', { params: { query: { page, page_size: PAGE_SIZE } } })),
    placeholderData: keepPreviousData,
    refetchInterval: (query) => (query.state.data?.results.some(isOrderOpen) ? 4000 : false),
  })

  return (
    <section className="card">
      <h2>Food orders</h2>
      <ErrorText error={orders.error} />
      {orders.data && orders.data.count === 0 && (
        <p className="muted">
          No orders yet. <Link to="/food">Find something to eat</Link>.
        </p>
      )}
      <ul className="list">
        {orders.data?.results.map((order) => {
          const stage = orderStage(order)
          const items = order.lines.reduce((sum, line) => sum + line.quantity, 0)
          return (
            <li key={order.id}>
              <Link to={`/orders/${order.id}`} className="restaurant-link">
                <span className="row between">
                  <strong>{order.restaurant.name}</strong>
                  <span className={`badge ${STAGE_BADGES[stage]}`}>{STAGE_LABELS[stage]}</span>
                </span>
                <span className="muted">
                  {dateTime.format(new Date(order.created_at))} · {items} {items === 1 ? 'item' : 'items'} ·{' '}
                  {formatFare(order.total)}
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
      {orders.data && orders.data.count > PAGE_SIZE && (
        <div className="row">
          <button className="secondary" disabled={!orders.data.previous} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span className="muted">
            Page {page} of {Math.ceil(orders.data.count / PAGE_SIZE)}
          </span>
          <button className="secondary" disabled={!orders.data.next} onClick={() => setPage((p) => p + 1)}>
            Next
          </button>
        </div>
      )}
    </section>
  )
}
