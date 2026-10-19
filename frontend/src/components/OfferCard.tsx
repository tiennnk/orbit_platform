import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Schemas } from '../api/client'
import { unwrap } from '../api/errors'
import { useNow } from '../hooks/useNow'
import { ErrorText } from './ErrorText'
import { formatFare } from './rideFormat'

type Offer = Schemas['RideOffer']

export function OfferCard({ offer }: { offer: Offer }) {
  const queryClient = useQueryClient()
  const now = useNow(500)
  const secondsLeft = Math.max(0, Math.ceil((new Date(offer.expires_at).getTime() - now) / 1000))

  const refresh = () =>
    Promise.all(
      ['current-offer', 'current-ride', 'my-driver'].map((key) =>
        queryClient.invalidateQueries({ queryKey: [key] }),
      ),
    )

  const respond = useMutation({
    mutationFn: (answer: 'accept' | 'decline') =>
      answer === 'accept'
        ? unwrap(api.POST('/api/v1/rides/offers/{id}/accept/', { params: { path: { id: offer.id } } }))
        : unwrap(api.POST('/api/v1/rides/offers/{id}/decline/', { params: { path: { id: offer.id } } })),
    onSettled: refresh,
  })

  return (
    <section className="card offer">
      <div className="row between">
        <h3>{offer.ride.service === 'food' ? 'New delivery request' : 'New ride request'}</h3>
        <span className="countdown">{secondsLeft}s</span>
      </div>
      <dl className="facts">
        {offer.ride.pickup_label && (
          <>
            <dt>{offer.ride.service === 'food' ? 'Pick up at' : 'Pickup'}</dt>
            <dd>{offer.ride.pickup_label}</dd>
          </>
        )}
        {offer.ride.dropoff_label && (
          <>
            <dt>Deliver to</dt>
            <dd>{offer.ride.dropoff_label}</dd>
          </>
        )}
        <dt>Distance</dt>
        <dd>{offer.ride.estimated_distance_km.toFixed(1)} km</dd>
        <dt>Fare</dt>
        <dd>{formatFare(offer.ride.estimated_fare)}</dd>
      </dl>
      <div className="row">
        <button disabled={respond.isPending || secondsLeft === 0} onClick={() => respond.mutate('accept')}>
          Accept
        </button>
        <button
          className="secondary"
          disabled={respond.isPending || secondsLeft === 0}
          onClick={() => respond.mutate('decline')}
        >
          Decline
        </button>
      </div>
      <ErrorText error={respond.error} />
    </section>
  )
}
