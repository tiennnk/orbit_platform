import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { useCurrentRide } from '../api/queries'
import { ErrorText } from '../components/ErrorText'
import { MapView, type MapPoint } from '../components/MapView'
import { RideCard } from '../components/RideCard'
import { useAuth } from '../auth/useAuth'

type Spot = { lat: number; lng: number }

export function RiderPage() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const current = useCurrentRide()
  const [pickup, setPickup] = useState<Spot | null>(null)
  const [dropoff, setDropoff] = useState<Spot | null>(null)
  const [picking, setPicking] = useState<'pickup' | 'dropoff'>('pickup')
  const [lastRideId, setLastRideId] = useState<number | null>(null)

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['current-ride'] })

  const lastRide = useQuery({
    queryKey: ['ride', lastRideId],
    queryFn: () => unwrap(api.GET('/api/v1/rides/{id}/', { params: { path: { id: lastRideId! } } })),
    enabled: lastRideId !== null && current.data === null,
  })

  const requestRide = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST('/api/v1/rides/', {
          body: {
            pickup_latitude: pickup!.lat,
            pickup_longitude: pickup!.lng,
            dropoff_latitude: dropoff!.lat,
            dropoff_longitude: dropoff!.lng,
          },
        }),
      ),
    onSuccess: (ride) => {
      setLastRideId(ride.id)
      return refresh()
    },
  })

  const cancelRide = useMutation({
    mutationFn: (id: number) => unwrap(api.POST('/api/v1/rides/{id}/cancel/', { params: { path: { id } } })),
    onSuccess: refresh,
  })

  if (current.isPending) {
    return <p className="muted">Loading...</p>
  }

  const ride = current.data
  if (ride && ride.rider_id !== user?.id) {
    return <p className="muted">You are driving ride #{ride.id} right now. See the Drive tab.</p>
  }

  if (ride) {
    const points: MapPoint[] = [
      { id: 'pickup', lat: ride.pickup_latitude, lng: ride.pickup_longitude, color: '#1d7a46', label: 'Pickup' },
      { id: 'dropoff', lat: ride.dropoff_latitude, lng: ride.dropoff_longitude, color: '#b42318', label: 'Dropoff' },
    ]
    return (
      <div className="split">
        <div>
          <RideCard ride={ride}>
            {(ride.status === 'searching' || ride.status === 'assigned') && (
              <button className="secondary" disabled={cancelRide.isPending} onClick={() => cancelRide.mutate(ride.id)}>
                Cancel ride
              </button>
            )}
          </RideCard>
          <ErrorText error={cancelRide.error} />
        </div>
        <MapView points={points} center={[ride.pickup_latitude, ride.pickup_longitude]} />
      </div>
    )
  }

  function pick(lat: number, lng: number) {
    if (picking === 'pickup') {
      setPickup({ lat, lng })
      setPicking('dropoff')
    } else {
      setDropoff({ lat, lng })
    }
  }

  const points: MapPoint[] = []
  if (pickup) points.push({ id: 'pickup', ...pickup, color: '#1d7a46', label: 'Pickup' })
  if (dropoff) points.push({ id: 'dropoff', ...dropoff, color: '#b42318', label: 'Dropoff' })

  return (
    <div className="split">
      <section className="card">
        {lastRide.data && (
          <div className="notice">
            <p>
              {lastRide.data.status === 'no_driver'
                ? 'No driver accepted your last request. Try again in a moment.'
                : lastRide.data.status === 'completed'
                  ? 'Your last trip is complete. Thanks for riding!'
                  : 'Your last ride was cancelled.'}
            </p>
            <button className="link" onClick={() => setLastRideId(null)}>
              Dismiss
            </button>
          </div>
        )}
        <h2>Where to?</h2>
        <p className="muted">Click the map to set your {picking}.</p>
        <div className="row">
          <button className={picking === 'pickup' ? '' : 'secondary'} onClick={() => setPicking('pickup')}>
            Set pickup
          </button>
          <button className={picking === 'dropoff' ? '' : 'secondary'} onClick={() => setPicking('dropoff')}>
            Set dropoff
          </button>
        </div>
        <dl className="facts">
          <dt>Pickup</dt>
          <dd>{pickup ? `${pickup.lat.toFixed(5)}, ${pickup.lng.toFixed(5)}` : '-'}</dd>
          <dt>Dropoff</dt>
          <dd>{dropoff ? `${dropoff.lat.toFixed(5)}, ${dropoff.lng.toFixed(5)}` : '-'}</dd>
        </dl>
        <button disabled={!pickup || !dropoff || requestRide.isPending} onClick={() => requestRide.mutate()}>
          {requestRide.isPending ? 'Finding a driver...' : 'Request ride'}
        </button>
        <ErrorText error={requestRide.error} />
      </section>
      <MapView points={points} onPick={pick} />
    </div>
  )
}
