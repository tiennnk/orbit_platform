import { NavLink, Outlet } from 'react-router'
import { useAuth } from '../auth/useAuth'

export function Layout() {
  const { user, logout } = useAuth()

  return (
    <>
      <header className="topbar">
        <strong className="brand">Orbit</strong>
        {user && (
          <nav>
            <NavLink to="/ride">Ride</NavLink>
            <NavLink to="/drive">Drive</NavLink>
            <NavLink to="/trips">Trips</NavLink>
            {user.is_staff && <NavLink to="/admin">Admin</NavLink>}
          </nav>
        )}
        {user && (
          <div className="row">
            <span className="muted">{user.username}</span>
            <button className="link" onClick={() => void logout()}>
              Log out
            </button>
          </div>
        )}
      </header>
      <main className="page">
        <Outlet />
      </main>
    </>
  )
}
