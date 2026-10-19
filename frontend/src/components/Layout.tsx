import { NavLink, Outlet } from 'react-router'
import { useMyDriver, useMyRestaurant } from '../api/queries'
import { useAuth } from '../auth/useAuth'
import { ChatBox } from './ChatBox'

function MemberNav() {
  const myDriver = useMyDriver()
  const myRestaurant = useMyRestaurant()
  const isDriver = Boolean(myDriver.data)
  const isMerchant = Boolean(myRestaurant.data)

  return (
    <nav>
      <NavLink to="/ride">Ride</NavLink>
      <NavLink to="/food">Food</NavLink>
      <NavLink to="/orders">Orders</NavLink>
      {isDriver && <NavLink to="/drive">Drive</NavLink>}
      {isMerchant && <NavLink to="/restaurant">Restaurant</NavLink>}
      <NavLink to="/trips">Trips</NavLink>
      <span className="nav-aside">
        {myDriver.data === null && <NavLink to="/drive">Become a driver</NavLink>}
        {myRestaurant.data === null && <NavLink to="/restaurant">Open a restaurant</NavLink>}
      </span>
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
            <NavLink to="/account" className="account-link">
              {user.username}
            </NavLink>
            <button className="link" onClick={() => void logout()}>
              Log out
            </button>
          </div>
        )}
      </header>
      <main className="page">
        <Outlet />
      </main>
      {user && !user.is_staff && <ChatBox />}
    </>
  )
}
