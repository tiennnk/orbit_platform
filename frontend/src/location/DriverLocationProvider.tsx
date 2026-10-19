import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { useMyDriver } from '../api/queries'
import { useAuth } from '../auth/useAuth'
import { useDevicePosition, useLocationReporter, type Position } from '../hooks/useLocationReporter'
import { DriverLocationContext, type DriverLocationState } from './context'

export function DriverLocationProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const myDriver = useMyDriver(user !== null && !user.is_staff)
  const online = myDriver.data?.is_online ?? false

  const [manual, setManual] = useState<{ userId: number; position: Position } | null>(null)
  const manualPosition = manual && user && manual.userId === user.id ? manual.position : null
  const setManualPosition = useCallback(
    (next: Position | null) => setManual(next && user ? { userId: user.id, position: next } : null),
    [user],
  )
  const device = useDevicePosition(online)
  const position = manualPosition ?? device.position
  const reporter = useLocationReporter(online, position)

  const value = useMemo<DriverLocationState>(
    () => ({
      position,
      usingManualPosition: manualPosition !== null,
      setManualPosition,
      deviceError: device.error,
      lastSentAt: reporter.lastSentAt,
      reportError: reporter.error,
    }),
    [position, manualPosition, setManualPosition, device.error, reporter.lastSentAt, reporter.error],
  )

  return <DriverLocationContext value={value}>{children}</DriverLocationContext>
}
