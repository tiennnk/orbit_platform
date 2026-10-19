import { use } from 'react'
import { DriverLocationContext } from './context'

export function useDriverLocation() {
  const state = use(DriverLocationContext)
  if (!state) {
    throw new Error('useDriverLocation must be used inside DriverLocationProvider')
  }
  return state
}
