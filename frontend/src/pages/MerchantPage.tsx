import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { api, type MenuItem, type RestaurantDetail } from '../api/client'
import { unwrap } from '../api/errors'
import { useMyRestaurant } from '../api/queries'
import { ErrorText } from '../components/ErrorText'
import { MapView } from '../components/MapView'
import { DEFAULT_CENTER } from '../components/mapDefaults'
import { formatFare } from '../components/rideFormat'

type Profile = { name: string; phone: string; address: string; latitude: number; longitude: number }

function useRefreshRestaurant() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: ['my-restaurant'] })
}

export function MerchantPage() {
  const mine = useMyRestaurant()

  if (mine.isPending) {
    return <p className="muted">Loading...</p>
  }
  if (mine.error) {
    return <ErrorText error={mine.error} />
  }
  if (!mine.data) {
    return (
      <ProfileForm
        title="Open a restaurant"
        submitLabel="Submit for approval"
        save={(body) => unwrap(api.POST('/api/v1/food/restaurants/', { body }))}
      />
    )
  }
  return <RestaurantConsole restaurant={mine.data} />
}

type ProfileFormProps = {
  title: string
  submitLabel: string
  initial?: Profile
  save: (body: Profile) => Promise<unknown>
  onCancel?: () => void
}

function ProfileForm({ title, submitLabel, initial, save, onCancel }: ProfileFormProps) {
  const refresh = useRefreshRestaurant()
  const [name, setName] = useState(initial?.name ?? '')
  const [phone, setPhone] = useState(initial?.phone ?? '')
  const [address, setAddress] = useState(initial?.address ?? '')
  const [spot, setSpot] = useState<[number, number] | null>(
    initial ? [initial.latitude, initial.longitude] : null,
  )

  const mutation = useMutation({
    mutationFn: () => save({ name, phone, address, latitude: spot![0], longitude: spot![1] }),
    onSuccess: async () => {
      await refresh()
      onCancel?.()
    },
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    mutation.mutate()
  }

  return (
    <div className="split">
      <form className="card" onSubmit={submit}>
        <h2>{title}</h2>
        <label>
          Restaurant name
          <input value={name} onChange={(e) => setName(e.target.value)} maxLength={120} required />
        </label>
        <label>
          Phone
          <input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" maxLength={20} required />
        </label>
        <label>
          Address
          <input value={address} onChange={(e) => setAddress(e.target.value)} maxLength={255} required />
        </label>
        <p className="muted">
          {spot ? `Location: ${spot[0].toFixed(5)}, ${spot[1].toFixed(5)}` : 'Click the map to set the location.'}
        </p>
        <ErrorText error={mutation.error} />
        <div className="row">
          <button type="submit" disabled={!spot || mutation.isPending}>
            {submitLabel}
          </button>
          {onCancel && (
            <button type="button" className="secondary" onClick={onCancel}>
              Cancel
            </button>
          )}
        </div>
      </form>
      <MapView
        points={spot ? [{ id: 'restaurant', lat: spot[0], lng: spot[1], color: '#0c969b', label: name || 'Restaurant' }] : []}
        center={spot ?? DEFAULT_CENTER}
        onPick={(lat, lng) => setSpot([lat, lng])}
      />
    </div>
  )
}

function RestaurantConsole({ restaurant }: { restaurant: RestaurantDetail }) {
  const refresh = useRefreshRestaurant()
  const [editing, setEditing] = useState(false)
  const canEdit = restaurant.approval_status === 'pending' || restaurant.approval_status === 'rejected'

  const toggleOpen = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST(restaurant.is_open ? '/api/v1/food/restaurants/me/close/' : '/api/v1/food/restaurants/me/open/'),
      ),
    onSuccess: refresh,
  })

  if (editing) {
    return (
      <ProfileForm
        title="Edit restaurant"
        submitLabel="Save and resubmit"
        initial={restaurant}
        save={(body) => unwrap(api.PUT('/api/v1/food/restaurants/me/', { body }))}
        onCancel={() => setEditing(false)}
      />
    )
  }

  return (
    <div className="split">
      <section className="card">
        <div className="row between">
          <h2>{restaurant.name}</h2>
          <span className={`badge badge-${restaurant.approval_status}`}>{restaurant.approval_status}</span>
        </div>
        <dl className="facts">
          <dt>Address</dt>
          <dd>{restaurant.address}</dd>
          <dt>Phone</dt>
          <dd>{restaurant.phone}</dd>
          <dt>Status</dt>
          <dd>{restaurant.is_open ? 'Open for orders' : 'Closed'}</dd>
        </dl>
        {restaurant.approval_status === 'pending' && (
          <p className="muted">Waiting for an admin to approve your restaurant.</p>
        )}
        {restaurant.approval_status === 'rejected' && (
          <p className="error">Your restaurant was rejected. Fix the details and submit again.</p>
        )}
        {restaurant.approval_status === 'suspended' && (
          <p className="error">Your restaurant is suspended. Contact support to get it reinstated.</p>
        )}
        <div className="row">
          {restaurant.approval_status === 'approved' && (
            <button
              className={restaurant.is_open ? 'secondary' : ''}
              disabled={toggleOpen.isPending}
              onClick={() => toggleOpen.mutate()}
            >
              {restaurant.is_open ? 'Close' : 'Open'}
            </button>
          )}
          {canEdit && (
            <button className="secondary" onClick={() => setEditing(true)}>
              Edit details
            </button>
          )}
        </div>
        <ErrorText error={toggleOpen.error} />
      </section>
      <MenuManager menu={restaurant.menu} />
    </div>
  )
}

type ItemDraft = { name: string; description: string; price: string; is_available: boolean }

const EMPTY_DRAFT: ItemDraft = { name: '', description: '', price: '', is_available: true }

function toBody(draft: ItemDraft) {
  return {
    name: draft.name,
    description: draft.description,
    price: Number(draft.price),
    is_available: draft.is_available,
  }
}

function MenuManager({ menu }: { menu: MenuItem[] }) {
  const refresh = useRefreshRestaurant()
  const [editingId, setEditingId] = useState<number | null>(null)

  const remove = useMutation({
    mutationFn: (id: number) => unwrap(api.DELETE('/api/v1/food/restaurants/me/menu/{id}/', { params: { path: { id } } })),
    onSuccess: refresh,
  })

  const toggle = useMutation({
    mutationFn: (item: MenuItem) =>
      unwrap(
        api.PUT('/api/v1/food/restaurants/me/menu/{id}/', {
          params: { path: { id: item.id } },
          body: {
            name: item.name,
            description: item.description,
            price: item.price,
            is_available: !item.is_available,
          },
        }),
      ),
    onSuccess: refresh,
  })

  return (
    <section className="card">
      <h2>Menu</h2>
      {menu.length === 0 && <p className="muted">No dishes yet. Add your first one below.</p>}
      <ul className="list">
        {menu.map((item) =>
          editingId === item.id ? (
            <li key={item.id}>
              <ItemForm
                initial={{ ...item, price: String(item.price) }}
                submitLabel="Save"
                save={(body) =>
                  unwrap(
                    api.PUT('/api/v1/food/restaurants/me/menu/{id}/', { params: { path: { id: item.id } }, body }),
                  )
                }
                onDone={() => setEditingId(null)}
              />
            </li>
          ) : (
            <li key={item.id} className={`menu-item${item.is_available ? '' : ' unavailable'}`}>
              <div className="row between">
                <strong>{item.name}</strong>
                <span>{formatFare(item.price)}</span>
              </div>
              {item.description && <p className="muted">{item.description}</p>}
              <div className="row">
                <button className="link" onClick={() => setEditingId(item.id)}>
                  Edit
                </button>
                <button className="link" disabled={toggle.isPending} onClick={() => toggle.mutate(item)}>
                  {item.is_available ? 'Mark sold out' : 'Mark available'}
                </button>
                <button className="link danger" disabled={remove.isPending} onClick={() => remove.mutate(item.id)}>
                  Delete
                </button>
              </div>
            </li>
          ),
        )}
      </ul>
      <ErrorText error={remove.error ?? toggle.error} />
      <h3>Add a dish</h3>
      <ItemForm
        initial={EMPTY_DRAFT}
        submitLabel="Add dish"
        save={(body) => unwrap(api.POST('/api/v1/food/restaurants/me/menu/', { body }))}
      />
    </section>
  )
}

type ItemFormProps = {
  initial: ItemDraft
  submitLabel: string
  save: (body: ReturnType<typeof toBody>) => Promise<unknown>
  onDone?: () => void
}

function ItemForm({ initial, submitLabel, save, onDone }: ItemFormProps) {
  const refresh = useRefreshRestaurant()
  const [draft, setDraft] = useState(initial)

  const mutation = useMutation({
    mutationFn: () => save(toBody(draft)),
    onSuccess: async () => {
      await refresh()
      if (onDone) {
        onDone()
      } else {
        setDraft(EMPTY_DRAFT)
      }
    },
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    mutation.mutate()
  }

  return (
    <form className="stack item-form" onSubmit={submit}>
      <div className="row">
        <input
          value={draft.name}
          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          placeholder="Dish name"
          aria-label="Dish name"
          maxLength={120}
          required
        />
        <input
          value={draft.price}
          onChange={(e) => setDraft({ ...draft, price: e.target.value })}
          placeholder="Price (VND)"
          aria-label="Price in VND"
          type="number"
          min={1}
          required
        />
      </div>
      <input
        value={draft.description}
        onChange={(e) => setDraft({ ...draft, description: e.target.value })}
        placeholder="Description (optional)"
        aria-label="Description"
        maxLength={500}
      />
      <ErrorText error={mutation.error} />
      <div className="row">
        <button type="submit" disabled={mutation.isPending}>
          {submitLabel}
        </button>
        {onDone && (
          <button type="button" className="secondary" onClick={onDone}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
