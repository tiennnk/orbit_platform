import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { unwrap } from '../api/errors'

export type Position = { lat: number; lng: number }

const REPORT_INTERVAL_MS = 5000

export function useDevicePosition(enabled: boolean) {
  const [position, setPosition] = useState<Position | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!enabled || !('geolocation' in navigator)) {
      return
    }
    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        setError(null)
        setPosition({ lat: pos.coords.latitude, lng: pos.coords.longitude })
      },
      (err) => setError(err.message),
      { enableHighAccuracy: true, maximumAge: 5000 },
    )
    return () => navigator.geolocation.clearWatch(watchId)
  }, [enabled])

  return { position, error }
}

export function useLocationReporter(enabled: boolean, position: Position | null) {
  const latest = useRef(position)
  const [lastSentAt, setLastSentAt] = useState<Date | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    latest.current = position
  }, [position])

  useEffect(() => {
    if (!enabled) {
      return
    }
    let cancelled = false

    async function send() {
      const current = latest.current
      if (!current) {
        return
      }
      try {
        await unwrap(
          api.PUT('/api/v1/drivers/me/location/', {
            body: {
              latitude: current.lat,
              longitude: current.lng,
              recorded_at: new Date().toISOString(),
            },
          }),
        )
        if (!cancelled) {
          setError(null)
          setLastSentAt(new Date())
        }
      } catch (err) {
        if (!cancelled) {
          setError(err)
        }
      }
    }

    void send()
    const timer = window.setInterval(() => void send(), REPORT_INTERVAL_MS)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [enabled])

  return { lastSentAt, error }
}
