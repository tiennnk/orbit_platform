import type { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router'
import { useAuth } from './auth/useAuth'
import { Layout } from './components/Layout'
import { AdminPage } from './pages/AdminPage'
import { AuthPage } from './pages/AuthPage'
import { DriverPage } from './pages/DriverPage'
import { RiderPage } from './pages/RiderPage'
import { TripsPage } from './pages/TripsPage'

function RequireAuth({ children, staff = false }: { children: ReactNode; staff?: boolean }) {
  const { user, loading } = useAuth()
  if (loading) {
    return <p className="muted">Loading...</p>
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  if (staff && !user.is_staff) {
    return <Navigate to="/ride" replace />
  }
  return children
}

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/register" element={<AuthPage mode="register" />} />
        <Route path="/ride" element={<RequireAuth><RiderPage /></RequireAuth>} />
        <Route path="/drive" element={<RequireAuth><DriverPage /></RequireAuth>} />
        <Route path="/trips" element={<RequireAuth><TripsPage /></RequireAuth>} />
        <Route path="/admin" element={<RequireAuth staff><AdminPage /></RequireAuth>} />
        <Route path="*" element={<Navigate to="/ride" replace />} />
      </Route>
    </Routes>
  )
}
