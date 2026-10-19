import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { api, type MenuItem, type RestaurantDetail } from '../api/client'
import { unwrap } from '../api/errors'
import { ErrorText } from '../components/ErrorText'
import { MapView, type MapPoint } from '../components/MapView'
import { formatFare } from '../components/rideFormat'

const MAX_QUANTITY = 20

type Cart = Record<number, number>

export function RestaurantPage() {
  const id = Number(useParams().id)

  const restaurant = useQuery({
    queryKey: ['restaurant', id],
    queryFn: () => unwrap(api.GET('/api/v1/food/restaurants/{id}/', { params: { path: { id } } })),
    enabled: Number.isInteger(id),
  })

  if (restaurant.isPending) {
    return <p className="muted">Loading...</p>
  }
  if (restaurant.error) {
    return (
      <section className="card narrow">
        <ErrorText error={restaurant.error} />
        <Link to="/food">Back to restaurants</Link>
      </section>
    )
  }
  return <RestaurantMenu restaurant={restaurant.data} />
}

function RestaurantMenu({ restaurant: r }: { restaurant: RestaurantDetail }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [cart, setCart] = useState<Cart>({})
  const [spot, setSpot] = useState<[number, number] | null>(null)
  const [address, setAddress] = useState('')
  const [note, setNote] = useState('')

  const lines = r.menu
    .filter((item) => cart[item.id])
    .map((item) => ({ item, quantity: cart[item.id] }))
  const subtotal = lines.reduce((sum, line) => sum + line.item.price * line.quantity, 0)

  const quote = useQuery({
    queryKey: ['delivery-quote', r.id, spot],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/food/restaurants/{id}/delivery-quote/', {
          params: { path: { id: r.id }, query: { latitude: spot![0], longitude: spot![1] } },
        }),
      ),
    enabled: spot !== null,
  })

  const placeOrder = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST('/api/v1/food/orders/', {
          body: {
            restaurant_id: r.id,
            items: lines.map((line) => ({ menu_item_id: line.item.id, quantity: line.quantity })),
            delivery_latitude: spot![0],
            delivery_longitude: spot![1],
            delivery_address: address,
            note,
          },
        }),
      ),
    onSuccess: async (order) => {
      await queryClient.invalidateQueries({ queryKey: ['my-orders'] })
      void navigate(`/orders/${order.id}`)
    },
  })

  function change(item: MenuItem, delta: number) {
    setCart((current) => {
      const next = Math.min(MAX_QUANTITY, Math.max(0, (current[item.id] ?? 0) + delta))
      const updated = { ...current, [item.id]: next }
      if (next === 0) {
        delete updated[item.id]
      }
      return updated
    })
  }

  const points: MapPoint[] = [{ id: 'restaurant', lat: r.latitude, lng: r.longitude, color: '#0c969b', label: r.name }]
  if (spot) points.push({ id: 'delivery', lat: spot[0], lng: spot[1], color: '#b42318', label: 'Deliver here' })

  const canOrder = r.is_open && lines.length > 0 && spot !== null && quote.data?.deliverable === true

  return (
    <div className="split">
      <div className="stack">
        <section className="card">
          <Link to="/food" className="muted">
            Back to restaurants
          </Link>
          <div className="row between">
            <h2>{r.name}</h2>
            <span className={`badge ${r.is_open ? 'badge-approved' : 'badge-cancelled'}`}>
              {r.is_open ? 'Open' : 'Closed'}
            </span>
          </div>
          <p className="muted">{[r.address, r.phone].filter(Boolean).join(' · ')}</p>
          <h3>Menu</h3>
          {r.menu.length === 0 && <p className="muted">This restaurant has not added any dishes yet.</p>}
          <ul className="list">
            {r.menu.map((item) => (
              <li key={item.id} className={`menu-item${item.is_available ? '' : ' unavailable'}`}>
                <div className="row between">
                  <strong>{item.name}</strong>
                  <span>{formatFare(item.price)}</span>
                </div>
                {item.description && <p className="muted">{item.description}</p>}
                {!item.is_available && <p className="muted">Sold out</p>}
                {item.is_available && r.is_open && (
                  <div className="row stepper">
                    <button
                      type="button"
                      className="secondary"
                      aria-label={`Remove one ${item.name}`}
                      disabled={!cart[item.id]}
                      onClick={() => change(item, -1)}
                    >
                      -
                    </button>
                    <span>{cart[item.id] ?? 0}</span>
                    <button
                      type="button"
                      className="secondary"
                      aria-label={`Add one ${item.name}`}
                      disabled={(cart[item.id] ?? 0) >= MAX_QUANTITY}
                      onClick={() => change(item, 1)}
                    >
                      +
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
          {!r.is_open && <p className="muted">This restaurant is closed, so you can only look at the menu.</p>}
        </section>

        {lines.length > 0 && (
          <section className="card">
            <h3>Your order</h3>
            <ul className="list">
              {lines.map(({ item, quantity }) => (
                <li key={item.id} className="row between">
                  <span>
                    {quantity} x {item.name}
                  </span>
                  <span>{formatFare(item.price * quantity)}</span>
                </li>
              ))}
            </ul>
            <dl className="facts">
              <dt>Subtotal</dt>
              <dd>{formatFare(subtotal)}</dd>
              <dt>Delivery</dt>
              <dd>
                {!spot
                  ? 'Click the map to set where to deliver'
                  : quote.data
                    ? `${formatFare(quote.data.delivery_fee)} (${quote.data.distance_km.toFixed(1)} km)`
                    : '...'}
              </dd>
              <dt>Total</dt>
              <dd>
                <strong>{formatFare(subtotal + (quote.data?.delivery_fee ?? 0))}</strong>
              </dd>
            </dl>
            {quote.data && !quote.data.deliverable && (
              <p className="error">This address is too far for this restaurant.</p>
            )}
            <label>
              Address details
              <input
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="House number, street, building"
                maxLength={255}
              />
            </label>
            <label>
              Note for the restaurant
              <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="No chili, extra sauce..." maxLength={300} />
            </label>
            <p className="muted">Pay the driver in cash when the food arrives.</p>
            <ErrorText error={quote.error ?? placeOrder.error} />
            <button disabled={!canOrder || placeOrder.isPending} onClick={() => placeOrder.mutate()}>
              {placeOrder.isPending ? 'Placing order...' : 'Place order'}
            </button>
          </section>
        )}
      </div>
      <MapView points={points} center={[r.latitude, r.longitude]} onPick={(lat, lng) => setSpot([lat, lng])} />
    </div>
  )
}
