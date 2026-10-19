import type { Ride } from '../api/client'
import { STATUS_LABELS, formatFare } from './rideFormat'

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
        <dd>{formatFare(ride.estimated_fare)}</dd>
      </dl>
      {children && <div className="row">{children}</div>}
    </section>
  )
}
