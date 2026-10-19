import type { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router'
import { homePath } from './auth/homePath'
import { useAuth } from './auth/useAuth'
import { Layout } from './components/Layout'
import { AccountPage } from './pages/AccountPage'
import { AdminPage } from './pages/AdminPage'
import { AuthPage } from './pages/AuthPage'
import { DriverPage } from './pages/DriverPage'
import { FoodPage } from './pages/FoodPage'
import { MerchantPage } from './pages/MerchantPage'
import { OrderPage } from './pages/OrderPage'
import { OrdersPage } from './pages/OrdersPage'
import { RestaurantPage } from './pages/RestaurantPage'
import { RiderPage } from './pages/RiderPage'
import { TripsPage } from './pages/TripsPage'

function RequireAuth({ children, staff = false }: { children: ReactNode; staff?: boolean | 'any' }) {
  const { user, loading } = useAuth()
  if (loading) {
    return <p className="muted">Loading...</p>
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  if (staff !== 'any' && staff !== user.is_staff) {
    return <Navigate to={homePath(user)} replace />
  }
  return children
}

function Home() {
  const { user, loading } = useAuth()
  if (loading) {
    return <p className="muted">Loading...</p>
  }
  return <Navigate to={user ? homePath(user) : '/login'} replace />
}

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/register" element={<AuthPage mode="register" />} />
        <Route path="/ride" element={<RequireAuth><RiderPage /></RequireAuth>} />
        <Route path="/drive" element={<RequireAuth><DriverPage /></RequireAuth>} />
        <Route path="/food" element={<RequireAuth><FoodPage /></RequireAuth>} />
        <Route path="/food/:id" element={<RequireAuth><RestaurantPage /></RequireAuth>} />
        <Route path="/restaurant" element={<RequireAuth><MerchantPage /></RequireAuth>} />
        <Route path="/orders" element={<RequireAuth><OrdersPage /></RequireAuth>} />
        <Route path="/orders/:id" element={<RequireAuth><OrderPage /></RequireAuth>} />
        <Route path="/trips" element={<RequireAuth><TripsPage /></RequireAuth>} />
        <Route path="/admin" element={<RequireAuth staff><AdminPage /></RequireAuth>} />
        <Route path="/account" element={<RequireAuth staff="any"><AccountPage /></RequireAuth>} />
        <Route path="*" element={<Home />} />
      </Route>
    </Routes>
  )
}
