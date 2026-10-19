import type { Ride } from '../api/client'
import { STATUS_LABELS, formatFare, formatRating } from './rideFormat'

export function RideCard({ ride, children }: { ride: Ride; children?: React.ReactNode }) {
  return (
    <section className="card">
      <div className="row between">
        <h3>
          {ride.service === 'food' ? 'Delivery' : 'Ride'} #{ride.id}
        </h3>
        <span className={`badge badge-${ride.status}`}>{STATUS_LABELS[ride.status]}</span>
      </div>
      <dl className="facts">
        {ride.pickup_label && (
          <>
            <dt>{ride.service === 'food' ? 'Pick up at' : 'Pickup'}</dt>
            <dd>{ride.pickup_label}</dd>
          </>
        )}
        {ride.dropoff_label && (
          <>
            <dt>{ride.service === 'food' ? 'Deliver to' : 'Dropoff'}</dt>
            <dd>{ride.dropoff_label}</dd>
          </>
        )}
        <dt>Driver</dt>
        <dd>{ride.driver ? `${ride.driver.full_name} (${ride.driver.phone})` : 'Waiting for a driver to accept'}</dd>
        {ride.driver && (
          <>
            <dt>Rating</dt>
            <dd>{formatRating(ride.driver.rating_average, ride.driver.rating_count)}</dd>
          </>
        )}
        <dt>Distance</dt>
        <dd>{ride.estimated_distance_km.toFixed(1)} km</dd>
        <dt>Fare</dt>
        <dd>{formatFare(ride.estimated_fare)}</dd>
      </dl>
      {children && <div className="row">{children}</div>}
    </section>
  )
}
