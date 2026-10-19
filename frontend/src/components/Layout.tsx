import { NavLink, Outlet } from 'react-router'
import { useMyDriver } from '../api/queries'
import { useAuth } from '../auth/useAuth'

function MemberNav() {
  const myDriver = useMyDriver()
  const isDriver = Boolean(myDriver.data)

  return (
    <nav>
      <NavLink to="/ride">Ride</NavLink>
      {isDriver && <NavLink to="/drive">Drive</NavLink>}
      <NavLink to="/trips">Trips</NavLink>
      {myDriver.data === null && (
        <NavLink to="/drive" className="nav-aside">
          Become a driver
        </NavLink>
      )}
    </nav>
  )
}

export function Layout() {
  const { user, logout } = useAuth()

  return (
    <>
      <header className="topbar">
        <strong className="brand">Orbit</strong>
        {user &&
          (user.is_staff ? (
            <nav>
              <NavLink to="/admin">Admin</NavLink>
            </nav>
          ) : (
            <MemberNav />
          ))}
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
