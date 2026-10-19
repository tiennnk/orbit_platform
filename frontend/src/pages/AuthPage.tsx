import { useState, type FormEvent } from 'react'
import { Link, Navigate } from 'react-router'
import { ErrorText } from '../components/ErrorText'
import { useAuth } from '../auth/useAuth'

export function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { user, login, register } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) {
    return <Navigate to="/ride" replace />
  }

  const isLogin = mode === 'login'

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await (isLogin ? login : register)(username, password)
    } catch (err) {
      setError(err)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="card narrow" onSubmit={submit}>
      <h2>{isLogin ? 'Log in' : 'Create account'}</h2>
      <label>
        Username
        <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
      </label>
      <label>
        Password
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete={isLogin ? 'current-password' : 'new-password'}
          required
        />
      </label>
      <ErrorText error={error} />
      <button type="submit" disabled={submitting}>
        {isLogin ? 'Log in' : 'Sign up'}
      </button>
      <p className="muted">
        {isLogin ? (
          <>
            No account yet? <Link to="/register">Sign up</Link>
          </>
        ) : (
          <>
            Already have an account? <Link to="/login">Log in</Link>
          </>
        )}
      </p>
    </form>
  )
}
