import { useQuery } from '@tanstack/react-query'
import type { Map as LeafletMap } from 'leaflet'
import { useState, type FormEvent } from 'react'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { ErrorText } from './ErrorText'

type Search = { q: string; latitude: number; longitude: number }

export function MapSearch({ map, onPick }: { map: LeafletMap | null; onPick: (lat: number, lng: number) => void }) {
  const [text, setText] = useState('')
  const [search, setSearch] = useState<Search | null>(null)

  const results = useQuery({
    queryKey: ['places', search],
    queryFn: () => unwrap(api.GET('/api/v1/places/search/', { params: { query: search! } })),
    enabled: search !== null,
    staleTime: Infinity,
    retry: false,
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    const q = text.trim()
    if (q.length < 2 || !map) {
      return
    }
    const center = map.getCenter()
    setSearch({ q, latitude: center.lat, longitude: center.lng })
  }

  function choose(lat: number, lng: number) {
    map?.flyTo([lat, lng], 16)
    onPick(lat, lng)
    setSearch(null)
  }

  return (
    <div className="map-search">
      <form className="row" onSubmit={submit}>
        <input
          type="search"
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            if (!e.target.value) {
              setSearch(null)
            }
          }}
          placeholder="Search for a place or address"
          aria-label="Search places"
        />
        <button type="submit" disabled={text.trim().length < 2 || results.isFetching}>
          {results.isFetching ? 'Searching...' : 'Search'}
        </button>
      </form>
      <ErrorText error={results.error} />
      {search && results.data && (
        <ul className="map-search-results">
          {results.data.length === 0 && <li className="muted">No places found.</li>}
          {results.data.map((place) => (
            <li key={`${place.latitude},${place.longitude},${place.address}`}>
              <button type="button" onClick={() => choose(place.latitude, place.longitude)}>
                <strong>{place.name}</strong>
                <span className="muted">{place.address}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
