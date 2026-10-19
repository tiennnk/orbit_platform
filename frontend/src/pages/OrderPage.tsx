import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { useDriverPosition } from '../api/queries'
import { ErrorText } from '../components/ErrorText'
import { MapView, type MapPoint } from '../components/MapView'
import { STAGE_BADGES, STAGE_LABELS, isOrderOpen, orderStage } from '../components/orderFormat'
import { formatFare, formatRating } from '../components/rideFormat'

export function OrderPage() {
  const id = Number(useParams().id)
  const queryClient = useQueryClient()

  const order = useQuery({
    queryKey: ['order', id],
    queryFn: () => unwrap(api.GET('/api/v1/food/orders/{id}/', { params: { path: { id } } })),
    enabled: Number.isInteger(id),
    refetchInterval: (query) => (query.state.data && isOrderOpen(query.state.data) ? 3000 : false),
  })

  const delivery = order.data?.delivery
  const tracking = delivery?.status === 'assigned' || delivery?.status === 'in_progress'
  const position = useDriverPosition(delivery?.id ?? 0, tracking)

  const cancel = useMutation({
    mutationFn: () => unwrap(api.POST('/api/v1/food/orders/{id}/cancel/', { params: { path: { id } } })),
    onSuccess: (updated) => {
      queryClient.setQueryData(['order', id], updated)
      return queryClient.invalidateQueries({ queryKey: ['my-orders'] })
    },
  })

  if (order.isPending) {
    return <p className="muted">Loading...</p>
  }
  if (order.error) {
    return (
      <section className="card narrow">
        <ErrorText error={order.error} />
        <Link to="/orders">Back to orders</Link>
      </section>
    )
  }

  const o = order.data
  const stage = orderStage(o)
  const driverAt = tracking ? position.data : null

  const points: MapPoint[] = [
    { id: 'restaurant', lat: o.restaurant.latitude, lng: o.restaurant.longitude, color: '#1d7a46', label: o.restaurant.name },
    { id: 'delivery', lat: o.delivery_latitude, lng: o.delivery_longitude, color: '#b42318', label: 'You' },
  ]
  if (driverAt) {
    points.push({ id: 'driver', lat: driverAt.latitude, lng: driverAt.longitude, color: '#0C969B', label: 'Driver' })
  }

  return (
    <div className="split">
      <div className="stack">
        {driverAt && (
          <p className="eta">
            {driverAt.heading_to === 'pickup'
              ? `Driver reaches the restaurant in about ${driverAt.eta_minutes} min`
              : `Your food arrives in about ${driverAt.eta_minutes} min (${driverAt.distance_km.toFixed(1)} km away)`}
          </p>
        )}
        <section className="card">
          <Link to="/orders" className="muted">
            Back to orders
          </Link>
          <div className="row between">
            <h2>Order #{o.id}</h2>
            <span className={`badge ${STAGE_BADGES[stage]}`}>{STAGE_LABELS[stage]}</span>
          </div>
          <p>
            <Link to={`/food/${o.restaurant.id}`}>{o.restaurant.name}</Link>
            <span className="muted"> · {o.restaurant.address}</span>
          </p>
          <ul className="list">
            {o.lines.map((line) => (
              <li key={line.name} className="row between">
                <span>
                  {line.quantity} x {line.name}
                </span>
                <span>{formatFare(line.line_total)}</span>
              </li>
            ))}
          </ul>
          <dl className="facts">
            <dt>Subtotal</dt>
            <dd>{formatFare(o.subtotal)}</dd>
            <dt>Delivery</dt>
            <dd>{formatFare(o.delivery_fee)}</dd>
            <dt>Total</dt>
            <dd>
              <strong>{formatFare(o.total)}</strong> (cash)
            </dd>
            {o.delivery_address && (
              <>
                <dt>Deliver to</dt>
                <dd>{o.delivery_address}</dd>
              </>
            )}
            {o.note && (
              <>
                <dt>Note</dt>
                <dd>{o.note}</dd>
              </>
            )}
            {delivery?.driver && (
              <>
                <dt>Driver</dt>
                <dd>
                  {delivery.driver.full_name} ({delivery.driver.phone}),{' '}
                  {formatRating(delivery.driver.rating_average, delivery.driver.rating_count)}
                </dd>
              </>
            )}
          </dl>
          {stage === 'no_driver' && (
            <p className="muted">No driver has taken the order yet. The restaurant will search again.</p>
          )}
          {o.status === 'placed' && (
            <button className="secondary" disabled={cancel.isPending} onClick={() => cancel.mutate()}>
              Cancel order
            </button>
          )}
          <ErrorText error={cancel.error} />
        </section>
      </div>
      <MapView points={points} center={[o.delivery_latitude, o.delivery_longitude]} />
    </div>
  )
}
