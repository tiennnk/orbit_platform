import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type Ride } from '../api/client'
import { unwrap } from '../api/errors'
import { ErrorText } from '../components/ErrorText'
import { STATUS_LABELS, formatFare } from '../components/rideFormat'

type Role = 'rider' | 'driver'

const PAGE_SIZE = 10

export function TripsPage() {
  const [role, setRole] = useState<Role>('rider')
  const [page, setPage] = useState(1)

  const history = useQuery({
    queryKey: ['ride-history', role, page],
    queryFn: () =>
      unwrap(api.GET('/api/v1/rides/history/', { params: { query: { role, page, page_size: PAGE_SIZE } } })),
    placeholderData: keepPreviousData,
  })

  function switchRole(next: Role) {
    setRole(next)
    setPage(1)
  }

  const totalPages = history.data ? Math.max(1, Math.ceil(history.data.count / PAGE_SIZE)) : 1

  return (
    <section className="card">
      <div className="row between">
        <h2>Trips</h2>
        <div className="row">
          <button className={role === 'rider' ? '' : 'secondary'} onClick={() => switchRole('rider')}>
            As rider
          </button>
          <button className={role === 'driver' ? '' : 'secondary'} onClick={() => switchRole('driver')}>
            As driver
          </button>
        </div>
      </div>

      <ErrorText error={history.error} />
      {history.data && history.data.count === 0 && <p className="muted">No trips yet.</p>}

      <ul className="list">
        {history.data?.results.map((ride) => <TripRow key={ride.id} ride={ride} role={role} />)}
      </ul>

      {history.data && history.data.count > PAGE_SIZE && (
        <div className="row">
          <button className="secondary" disabled={!history.data.previous} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span className="muted">
            Page {page} of {totalPages}
          </span>
          <button className="secondary" disabled={!history.data.next} onClick={() => setPage((p) => p + 1)}>
            Next
          </button>
        </div>
      )}
    </section>
  )
}

const dateTime = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

function TripRow({ ride, role }: { ride: Ride; role: Role }) {
  return (
    <li className="trip">
      <div className="row between">
        <strong>{dateTime.format(new Date(ride.created_at))}</strong>
        <span className={`badge badge-${ride.status}`}>{STATUS_LABELS[ride.status]}</span>
      </div>
      <div className="row between muted">
        <span>
          {role === 'rider' ? `Driver: ${ride.driver?.full_name ?? '-'}` : `Ride #${ride.id}`} ·{' '}
          {ride.estimated_distance_km.toFixed(1)} km
        </span>
        <span>{formatFare(ride.estimated_fare)}</span>
      </div>
    </li>
  )
}
