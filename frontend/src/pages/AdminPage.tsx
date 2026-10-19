import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type Driver } from '../api/client'
import { unwrap } from '../api/errors'
import { ErrorText } from '../components/ErrorText'
import { MapView, type MapPoint } from '../components/MapView'
import { DEFAULT_CENTER } from '../components/mapDefaults'

type Section = 'drivers' | 'restaurants'

export function AdminPage() {
  const [section, setSection] = useState<Section>('drivers')

  return (
    <div className="stack">
      <div className="row">
        <button className={section === 'drivers' ? '' : 'secondary'} onClick={() => setSection('drivers')}>
          Drivers
        </button>
        <button className={section === 'restaurants' ? '' : 'secondary'} onClick={() => setSection('restaurants')}>
          Restaurants
        </button>
      </div>
      {section === 'drivers' ? (
        <div className="split">
          <ModerationPanel kind="drivers" />
          <NearbyDrivers />
        </div>
      ) : (
        <ModerationPanel kind="restaurants" />
      )}
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

type Row = {
  id: number
  approval_status: ApprovalStatus
  title: string
  details: string[]
}

function runAction(kind: Section, id: number, action: Action): Promise<unknown> {
  const params = { params: { path: { id } } }
  if (kind === 'restaurants') {
    switch (action) {
      case 'approve':
        return unwrap(api.POST('/api/v1/food/restaurants/{id}/approve/', params))
      case 'reject':
        return unwrap(api.POST('/api/v1/food/restaurants/{id}/reject/', params))
      case 'suspend':
        return unwrap(api.POST('/api/v1/food/restaurants/{id}/suspend/', params))
      case 'reinstate':
        return unwrap(api.POST('/api/v1/food/restaurants/{id}/reinstate/', params))
    }
  }
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

async function fetchRows(kind: Section, status: ApprovalStatus, page: number) {
  const query = { approval_status: status, page, page_size: PAGE_SIZE }
  if (kind === 'restaurants') {
    const data = await unwrap(api.GET('/api/v1/food/restaurants/', { params: { query } }))
    return {
      ...data,
      results: data.results.map<Row>((r) => ({
        id: r.id,
        approval_status: r.approval_status,
        title: r.name,
        details: [r.address, r.phone, ...(r.is_open ? ['open'] : [])].filter(Boolean),
      })),
    }
  }
  const data = await unwrap(api.GET('/api/v1/drivers/', { params: { query } }))
  return {
    ...data,
    results: data.results.map<Row>((d) => ({
      id: d.id,
      approval_status: d.approval_status,
      title: d.full_name,
      details: [
        d.phone,
        ...(d.rating_count > 0 && d.rating_average !== null ? [`${d.rating_average.toFixed(1)} / 5`] : []),
        ...(d.is_online ? ['online'] : []),
      ],
    })),
  }
}

function ModerationPanel({ kind }: { kind: Section }) {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<ApprovalStatus>('pending')
  const [page, setPage] = useState(1)

  const rows = useQuery({
    queryKey: [kind, status, page],
    queryFn: () => fetchRows(kind, status, page),
  })

  const act = useMutation({
    mutationFn: ({ id, action }: { id: number; action: Action }) => runAction(kind, id, action),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [kind] }),
  })

  function switchStatus(next: ApprovalStatus) {
    setStatus(next)
    setPage(1)
  }

  return (
    <section className="card">
      <h2>{kind === 'drivers' ? 'Drivers' : 'Restaurants'}</h2>
      <div className="row">
        {STATUS_TABS.map((tab) => (
          <button key={tab} className={tab === status ? '' : 'secondary'} onClick={() => switchStatus(tab)}>
            {tab}
          </button>
        ))}
      </div>
      <ErrorText error={rows.error ?? act.error} />
      {rows.data && rows.data.results.length === 0 && (
        <p className="muted">
          No {status} {kind}.
        </p>
      )}
      <ul className="list">
        {rows.data?.results.map((row) => (
          <li key={row.id} className="row between">
            <span>
              {row.title}
              {row.details.map((detail) => (
                <span key={detail} className="muted">
                  {' '}
                  · {detail}
                </span>
              ))}
            </span>
            <span className="row">
              {ACTIONS[row.approval_status].map(({ action, label, secondary }) => (
                <button
                  key={action}
                  className={secondary ? 'secondary' : ''}
                  disabled={act.isPending}
                  onClick={() => act.mutate({ id: row.id, action })}
                >
                  {label}
                </button>
              ))}
            </span>
          </li>
        ))}
      </ul>
      {rows.data && rows.data.count > PAGE_SIZE && (
        <div className="row">
          <button className="secondary" disabled={!rows.data.previous} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span className="muted">
            Page {page} of {Math.ceil(rows.data.count / PAGE_SIZE)}
          </span>
          <button className="secondary" disabled={!rows.data.next} onClick={() => setPage((p) => p + 1)}>
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
