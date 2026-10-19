import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { api, type Driver } from '../api/client'
import { unwrap } from '../api/errors'
import { useCurrentOffer, useCurrentRide, useMyDriver } from '../api/queries'
import { ErrorText } from '../components/ErrorText'
import { MapView, type MapPoint } from '../components/MapView'
import { OfferCard } from '../components/OfferCard'
import { RideCard } from '../components/RideCard'
import { useDriverLocation } from '../location/useDriverLocation'

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

type ProfileFormProps = {
  title: string
  submitLabel: string
  initial?: { full_name: string; phone: string }
  save: (body: { full_name: string; phone: string }) => Promise<unknown>
  onDone?: () => void
  onCancel?: () => void
}

function ProfileForm({ title, submitLabel, initial, save, onDone, onCancel }: ProfileFormProps) {
  const queryClient = useQueryClient()
  const [fullName, setFullName] = useState(initial?.full_name ?? '')
  const [phone, setPhone] = useState(initial?.phone ?? '')

  const mutation = useMutation({
    mutationFn: () => save({ full_name: fullName, phone }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['my-driver'] })
      onDone?.()
    },
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    mutation.mutate()
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>{title}</h2>
      <label>
        Full name
        <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
      </label>
      <label>
        Phone
        <input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" required />
      </label>
      <ErrorText error={mutation.error} />
      <div className="row">
        <button type="submit" disabled={mutation.isPending}>
          {submitLabel}
        </button>
        {onCancel && (
          <button type="button" className="secondary" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}

function DriverSignup() {
  return (
    <div className="narrow">
      <ProfileForm
        title="Become a driver"
        submitLabel="Submit for approval"
        save={(body) => unwrap(api.POST('/api/v1/drivers/', { body }))}
      />
    </div>
  )
}

function DriverConsole({ driver }: { driver: Driver }) {
  const queryClient = useQueryClient()
  const current = useCurrentRide()
  const location = useDriverLocation()
  const position = location.position
  const [editing, setEditing] = useState(false)
  const canEdit = driver.approval_status === 'pending' || driver.approval_status === 'rejected'

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

  const ride = current.data && current.data.driver?.id === driver.id ? current.data : null
  const waitingForRides = driver.is_online && driver.availability === 'available'
  const offer = useCurrentOffer(waitingForRides)

  const points: MapPoint[] = []
  if (position) points.push({ id: 'me', ...position, color: '#0c969b', label: 'You' })
  if (offer.data) {
    const offered = offer.data.ride
    points.push({ id: 'offer-pickup', lat: offered.pickup_latitude, lng: offered.pickup_longitude, color: '#1d7a46', label: 'Pickup' })
    points.push({ id: 'offer-dropoff', lat: offered.dropoff_latitude, lng: offered.dropoff_longitude, color: '#b42318', label: 'Dropoff' })
  }
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
                ? location.lastSentAt
                  ? `Sent ${location.lastSentAt.toLocaleTimeString()}`
                  : 'Waiting for a position'
                : '-'}
            </dd>
          </dl>
          {driver.approval_status === 'pending' && <p className="muted">Waiting for an admin to approve your profile.</p>}
          {driver.approval_status === 'rejected' && (
            <p className="error">Your profile was rejected. Fix your details and submit again.</p>
          )}
          {driver.approval_status === 'suspended' && (
            <p className="error">Your account is suspended. Contact support to get it reinstated.</p>
          )}
          {canEdit && !editing && (
            <button className="secondary" onClick={() => setEditing(true)}>
              Edit profile
            </button>
          )}
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
          {driver.is_online && location.deviceError && !location.usingManualPosition && (
            <p className="muted">GPS unavailable ({location.deviceError}). Click the map to set your position.</p>
          )}
          {driver.is_online && (
            <p className="muted">Your location keeps updating while you're online, even on other tabs.</p>
          )}
          <ErrorText error={location.reportError} />
        </section>

        {canEdit && editing && (
          <ProfileForm
            title="Edit profile"
            submitLabel={driver.approval_status === 'rejected' ? 'Resubmit for approval' : 'Save'}
            initial={driver}
            save={(body) => unwrap(api.PUT('/api/v1/drivers/me/', { body }))}
            onDone={() => setEditing(false)}
            onCancel={() => setEditing(false)}
          />
        )}

        {waitingForRides && offer.data && <OfferCard key={offer.data.id} offer={offer.data} />}

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
        onPick={driver.is_online ? (lat, lng) => location.setManualPosition({ lat, lng }) : undefined}
      />
    </div>
  )
}
