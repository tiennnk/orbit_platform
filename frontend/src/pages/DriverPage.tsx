import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { api, type Driver } from '../api/client'
import { unwrap } from '../api/errors'
import { useCurrentRide, useMyDriver } from '../api/queries'
import { ErrorText } from '../components/ErrorText'
import { MapView, type MapPoint } from '../components/MapView'
import { RideCard } from '../components/RideCard'
import { useDevicePosition, useLocationReporter, type Position } from '../hooks/useLocationReporter'

export function DriverPage() {
  const myDriver = useMyDriver()

  if (myDriver.isPending) {
    return <p className="muted">Loading...</p>
  }
  if (myDriver.error) {
    return <ErrorText error={myDriver.error} />
  }
  if (!myDriver.data) {
    return <DriverSignup />
  }
  return <DriverConsole driver={myDriver.data} />
}

function DriverSignup() {
  const queryClient = useQueryClient()
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')

  const signup = useMutation({
    mutationFn: () => unwrap(api.POST('/api/v1/drivers/', { body: { full_name: fullName, phone } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['my-driver'] }),
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    signup.mutate()
  }

  return (
    <form className="card narrow" onSubmit={submit}>
      <h2>Become a driver</h2>
      <label>
        Full name
        <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
      </label>
      <label>
        Phone
        <input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" required />
      </label>
      <ErrorText error={signup.error} />
      <button type="submit" disabled={signup.isPending}>
        Submit for approval
      </button>
    </form>
  )
}

function DriverConsole({ driver }: { driver: Driver }) {
  const queryClient = useQueryClient()
  const current = useCurrentRide()
  const [manualPosition, setManualPosition] = useState<Position | null>(null)
  const device = useDevicePosition(driver.is_online)
  const position = manualPosition ?? device.position
  const reporter = useLocationReporter(driver.is_online, position)

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['my-driver'] })
    void queryClient.invalidateQueries({ queryKey: ['current-ride'] })
  }

  const toggleOnline = useMutation({
    mutationFn: () =>
      unwrap(api.POST(driver.is_online ? '/api/v1/drivers/me/offline/' : '/api/v1/drivers/me/online/')),
    onSuccess: refresh,
  })

  const rideAction = useMutation({
    mutationFn: ({ id, action }: { id: number; action: 'start' | 'complete' }) =>
      unwrap(
        action === 'start'
          ? api.POST('/api/v1/rides/{id}/start/', { params: { path: { id } } })
          : api.POST('/api/v1/rides/{id}/complete/', { params: { path: { id } } }),
      ),
    onSuccess: refresh,
  })

  const ride = current.data && current.data.driver.id === driver.id ? current.data : null

  const points: MapPoint[] = []
  if (position) points.push({ id: 'me', ...position, color: '#0c969b', label: 'You' })
  if (ride) {
    points.push({ id: 'pickup', lat: ride.pickup_latitude, lng: ride.pickup_longitude, color: '#1d7a46', label: 'Pickup' })
    points.push({ id: 'dropoff', lat: ride.dropoff_latitude, lng: ride.dropoff_longitude, color: '#b42318', label: 'Dropoff' })
  }

  return (
    <div className="split">
      <div className="stack">
        <section className="card">
          <div className="row between">
            <h2>{driver.full_name}</h2>
            <span className={`badge badge-${driver.approval_status}`}>{driver.approval_status}</span>
          </div>
          <dl className="facts">
            <dt>Phone</dt>
            <dd>{driver.phone}</dd>
            <dt>Status</dt>
            <dd>{driver.is_online ? (driver.availability === 'on_trip' ? 'On a trip' : 'Online, waiting') : 'Offline'}</dd>
            <dt>Location</dt>
            <dd>
              {driver.is_online
                ? reporter.lastSentAt
                  ? `Sent ${reporter.lastSentAt.toLocaleTimeString()}`
                  : 'Waiting for a position'
                : '-'}
            </dd>
          </dl>
          {driver.approval_status === 'pending' && <p className="muted">Waiting for an admin to approve your profile.</p>}
          {driver.approval_status === 'approved' && (
            <button
              className={driver.is_online ? 'secondary' : ''}
              disabled={toggleOnline.isPending}
              onClick={() => toggleOnline.mutate()}
            >
              {driver.is_online ? 'Go offline' : 'Go online'}
            </button>
          )}
          <ErrorText error={toggleOnline.error} />
          {driver.is_online && device.error && !manualPosition && (
            <p className="muted">GPS unavailable ({device.error}). Click the map to set your position.</p>
          )}
          <ErrorText error={reporter.error} />
        </section>

        {ride && (
          <RideCard ride={ride}>
            {ride.status === 'assigned' && (
              <button disabled={rideAction.isPending} onClick={() => rideAction.mutate({ id: ride.id, action: 'start' })}>
                Pick up rider
              </button>
            )}
            {ride.status === 'in_progress' && (
              <button
                disabled={rideAction.isPending}
                onClick={() => rideAction.mutate({ id: ride.id, action: 'complete' })}
              >
                Complete trip
              </button>
            )}
          </RideCard>
        )}
        <ErrorText error={rideAction.error} />
      </div>
      <MapView
        points={points}
        center={position ? [position.lat, position.lng] : undefined}
        onPick={driver.is_online ? (lat, lng) => setManualPosition({ lat, lng }) : undefined}
      />
    </div>
  )
}
