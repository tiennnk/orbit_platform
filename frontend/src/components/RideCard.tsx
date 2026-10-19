import type { Ride } from '../api/client'

const STATUS_LABELS: Record<Ride['status'], string> = {
  assigned: 'Driver on the way',
  in_progress: 'On trip',
  completed: 'Completed',
  cancelled: 'Cancelled',
}

const vnd = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' })

export function RideCard({ ride, children }: { ride: Ride; children?: React.ReactNode }) {
  return (
    <section className="card">
      <div className="row between">
        <h3>Ride #{ride.id}</h3>
        <span className={`badge badge-${ride.status}`}>{STATUS_LABELS[ride.status]}</span>
      </div>
      <dl className="facts">
        <dt>Driver</dt>
        <dd>
          {ride.driver.full_name} ({ride.driver.phone})
        </dd>
        <dt>Distance</dt>
        <dd>{ride.estimated_distance_km.toFixed(1)} km</dd>
        <dt>Fare</dt>
        <dd>{vnd.format(ride.estimated_fare)}</dd>
      </dl>
      {children && <div className="row">{children}</div>}
    </section>
  )
}
