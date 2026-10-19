import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { ErrorText } from '../components/ErrorText'
import { MapView } from '../components/MapView'
import { formatFare } from '../components/rideFormat'

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

  const r = restaurant.data
  return (
    <div className="split">
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
        <p className="muted">
          {[r.address, r.phone].filter(Boolean).join(' · ')}
        </p>
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
            </li>
          ))}
        </ul>
        <p className="muted">Ordering is coming soon.</p>
      </section>
      <MapView
        points={[{ id: 'restaurant', lat: r.latitude, lng: r.longitude, color: '#0c969b', label: r.name }]}
        center={[r.latitude, r.longitude]}
      />
    </div>
  )
}
