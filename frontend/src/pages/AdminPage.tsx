import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { ErrorText } from '../components/ErrorText'
import { MapView, type MapPoint } from '../components/MapView'
import { DEFAULT_CENTER } from '../components/mapDefaults'

export function AdminPage() {
  return (
    <div className="split">
      <PendingDrivers />
      <NearbyDrivers />
    </div>
  )
}

function PendingDrivers() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)

  const pending = useQuery({
    queryKey: ['drivers', 'pending', page],
    queryFn: () =>
      unwrap(api.GET('/api/v1/drivers/', { params: { query: { approval_status: 'pending', page } } })),
  })

  const approve = useMutation({
    mutationFn: (id: number) => unwrap(api.POST('/api/v1/drivers/{id}/approve/', { params: { path: { id } } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['drivers', 'pending'] }),
  })

  return (
    <section className="card">
      <h2>Pending drivers</h2>
      <ErrorText error={pending.error ?? approve.error} />
      {pending.data && pending.data.results.length === 0 && <p className="muted">Nothing to review.</p>}
      <ul className="list">
        {pending.data?.results.map((driver) => (
          <li key={driver.id} className="row between">
            <span>
              {driver.full_name} <span className="muted">{driver.phone}</span>
            </span>
            <button disabled={approve.isPending} onClick={() => approve.mutate(driver.id)}>
              Approve
            </button>
          </li>
        ))}
      </ul>
      {pending.data && (
        <div className="row">
          <button className="secondary" disabled={!pending.data.previous} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span className="muted">
            Page {page} of {Math.max(1, Math.ceil(pending.data.count / 20))}
          </span>
          <button className="secondary" disabled={!pending.data.next} onClick={() => setPage((p) => p + 1)}>
            Next
          </button>
        </div>
      )}
    </section>
  )
}

function NearbyDrivers() {
  const [center, setCenter] = useState<[number, number]>(DEFAULT_CENTER)
  const [radiusKm, setRadiusKm] = useState(3)

  const nearby = useQuery({
    queryKey: ['nearby', center, radiusKm],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/drivers/nearby/', {
          params: { query: { latitude: center[0], longitude: center[1], radius_km: radiusKm, limit: 20 } },
        }),
      ),
    refetchInterval: 5000,
  })

  const points: MapPoint[] = [
    { id: 'center', lat: center[0], lng: center[1], color: '#101828', label: 'Search point' },
    ...(nearby.data ?? []).map((n) => ({
      id: `driver-${n.driver_id}`,
      lat: n.latitude,
      lng: n.longitude,
      color: '#0c969b',
      label: `${n.full_name} (${n.distance_km.toFixed(2)} km)`,
    })),
  ]

  return (
    <div className="stack">
      <section className="card">
        <h2>Drivers nearby</h2>
        <p className="muted">Click the map to move the search point.</p>
        <label>
          Radius: {radiusKm} km
          <input type="range" min={1} max={20} value={radiusKm} onChange={(e) => setRadiusKm(Number(e.target.value))} />
        </label>
        <ErrorText error={nearby.error} />
        <p>{nearby.data ? `${nearby.data.length} available drivers` : 'Searching...'}</p>
      </section>
      <MapView points={points} center={center} onPick={(lat, lng) => setCenter([lat, lng])} />
    </div>
  )
}
