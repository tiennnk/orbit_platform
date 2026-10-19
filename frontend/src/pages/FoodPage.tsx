import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { ErrorText } from '../components/ErrorText'
import { MapView, type MapPoint } from '../components/MapView'
import { DEFAULT_CENTER } from '../components/mapDefaults'
import { useDebounced } from '../hooks/useDebounced'

export function FoodPage() {
  const [spot, setSpot] = useState<[number, number]>(DEFAULT_CENTER)
  const [text, setText] = useState('')
  const q = useDebounced(text.trim(), 300)

  const restaurants = useQuery({
    queryKey: ['restaurants-nearby', spot, q],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/food/restaurants/nearby/', {
          params: { query: { latitude: spot[0], longitude: spot[1], radius_km: 5, limit: 30, q } },
        }),
      ),
    placeholderData: keepPreviousData,
  })

  const points: MapPoint[] = [
    { id: 'you', lat: spot[0], lng: spot[1], color: '#101828', label: 'Deliver here' },
    ...(restaurants.data ?? []).map((r) => ({
      id: `restaurant-${r.id}`,
      lat: r.latitude,
      lng: r.longitude,
      color: r.is_open ? '#0c969b' : '#98a2b3',
      label: r.name,
    })),
  ]

  return (
    <div className="split">
      <section className="card">
        <h2>Food near you</h2>
        <p className="muted">Click the map or search a place to set where you are.</p>
        <label>
          Restaurant name
          <input type="search" value={text} onChange={(e) => setText(e.target.value)} placeholder="Pho, com tam..." />
        </label>
        <ErrorText error={restaurants.error} />
        {restaurants.data && restaurants.data.length === 0 && (
          <p className="muted">No restaurants within 5 km.</p>
        )}
        <ul className="list">
          {restaurants.data?.map((r) => (
            <li key={r.id}>
              <Link to={`/food/${r.id}`} className={`restaurant-link${r.is_open ? '' : ' closed'}`}>
                <span className="row between">
                  <strong>{r.name}</strong>
                  <span className="muted">{r.distance_km.toFixed(1)} km</span>
                </span>
                <span className="muted">
                  {r.address}
                  {!r.is_open && ' · closed'}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
      <MapView points={points} center={spot} onPick={(lat, lng) => setSpot([lat, lng])} />
    </div>
  )
}
