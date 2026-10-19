import type { Map as LeafletMap } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useState } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMapEvents } from 'react-leaflet'
import { MapSearch } from './MapSearch'
import { DEFAULT_CENTER } from './mapDefaults'

export type MapPoint = {
  id: string
  lat: number
  lng: number
  color: string
  label: string
}

type Props = {
  points: MapPoint[]
  center?: [number, number]
  onPick?: (lat: number, lng: number) => void
}

function ClickHandler({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(event) {
      onPick(event.latlng.lat, event.latlng.lng)
    },
  })
  return null
}

export function MapView({ points, center = DEFAULT_CENTER, onPick }: Props) {
  const [map, setMap] = useState<LeafletMap | null>(null)

  return (
    <div className="map-wrap">
      {onPick && <MapSearch map={map} onPick={onPick} />}
      <MapContainer center={center} zoom={13} className="map" ref={setMap}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {onPick && <ClickHandler onPick={onPick} />}
        {points.map((point) => (
          <CircleMarker
            key={point.id}
            center={[point.lat, point.lng]}
            radius={9}
            pathOptions={{ color: point.color, fillColor: point.color, fillOpacity: 0.85 }}
          >
            <Tooltip permanent direction="top" offset={[0, -8]}>
              {point.label}
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  )
}
