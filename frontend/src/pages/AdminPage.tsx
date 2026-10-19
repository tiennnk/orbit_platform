import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type Driver } from '../api/client'
import { unwrap } from '../api/errors'
import { ErrorText } from '../components/ErrorText'
import { MapView, type MapPoint } from '../components/MapView'
import { DEFAULT_CENTER } from '../components/mapDefaults'

export function AdminPage() {
  return (
    <div className="split">
      <DriversPanel />
      <NearbyDrivers />
    </div>
  )
}

type ApprovalStatus = Driver['approval_status']
type Action = 'approve' | 'reject' | 'suspend' | 'reinstate'

const STATUS_TABS: ApprovalStatus[] = ['pending', 'approved', 'suspended', 'rejected']

const ACTIONS: Record<ApprovalStatus, { action: Action; label: string; secondary?: boolean }[]> = {
  pending: [
    { action: 'approve', label: 'Approve' },
    { action: 'reject', label: 'Reject', secondary: true },
  ],
  approved: [{ action: 'suspend', label: 'Suspend', secondary: true }],
  suspended: [{ action: 'reinstate', label: 'Reinstate' }],
  rejected: [],
}

const PAGE_SIZE = 20

function runAction(id: number, action: Action) {
  const params = { params: { path: { id } } }
  switch (action) {
    case 'approve':
      return unwrap(api.POST('/api/v1/drivers/{id}/approve/', params))
    case 'reject':
      return unwrap(api.POST('/api/v1/drivers/{id}/reject/', params))
    case 'suspend':
      return unwrap(api.POST('/api/v1/drivers/{id}/suspend/', params))
    case 'reinstate':
      return unwrap(api.POST('/api/v1/drivers/{id}/reinstate/', params))
  }
}

function DriversPanel() {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<ApprovalStatus>('pending')
  const [page, setPage] = useState(1)

  const drivers = useQuery({
    queryKey: ['drivers', status, page],
    queryFn: () =>
      unwrap(api.GET('/api/v1/drivers/', { params: { query: { approval_status: status, page, page_size: PAGE_SIZE } } })),
  })

  const act = useMutation({
    mutationFn: ({ id, action }: { id: number; action: Action }) => runAction(id, action),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['drivers'] }),
  })

  function switchStatus(next: ApprovalStatus) {
    setStatus(next)
    setPage(1)
  }

  return (
    <section className="card">
      <h2>Drivers</h2>
      <div className="row">
        {STATUS_TABS.map((tab) => (
          <button key={tab} className={tab === status ? '' : 'secondary'} onClick={() => switchStatus(tab)}>
            {tab}
          </button>
        ))}
      </div>
      <ErrorText error={drivers.error ?? act.error} />
      {drivers.data && drivers.data.results.length === 0 && <p className="muted">No {status} drivers.</p>}
      <ul className="list">
        {drivers.data?.results.map((driver) => (
          <li key={driver.id} className="row between">
            <span>
              {driver.full_name} <span className="muted">{driver.phone}</span>
              {driver.rating_count > 0 && <span className="muted"> · {driver.rating_average?.toFixed(1)} / 5</span>}
              {driver.is_online && <span className="muted"> · online</span>}
            </span>
            <span className="row">
              {ACTIONS[driver.approval_status].map(({ action, label, secondary }) => (
                <button
                  key={action}
                  className={secondary ? 'secondary' : ''}
                  disabled={act.isPending}
                  onClick={() => act.mutate({ id: driver.id, action })}
                >
                  {label}
                </button>
              ))}
            </span>
          </li>
        ))}
      </ul>
      {drivers.data && drivers.data.count > PAGE_SIZE && (
        <div className="row">
          <button className="secondary" disabled={!drivers.data.previous} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span className="muted">
            Page {page} of {Math.ceil(drivers.data.count / PAGE_SIZE)}
          </span>
          <button className="secondary" disabled={!drivers.data.next} onClick={() => setPage((p) => p + 1)}>
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
