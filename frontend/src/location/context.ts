import { createContext } from 'react'
import type { Position } from '../hooks/useLocationReporter'

export type DriverLocationState = {
  position: Position | null
  usingManualPosition: boolean
  setManualPosition: (position: Position | null) => void
  deviceError: string | null
  lastSentAt: Date | null
  reportError: unknown
}

export const DriverLocationContext = createContext<DriverLocationState | null>(null)
