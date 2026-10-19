import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { setToken } from '../auth/token'
import { useAuth } from '../auth/useAuth'
import { ErrorText } from '../components/ErrorText'

export function AccountPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const mismatch = confirmPassword !== '' && confirmPassword !== newPassword

  const change = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST('/api/v1/auth/password/', {
          body: { current_password: currentPassword, new_password: newPassword },
        }),
      ),
    onSuccess: (result) => {
      queryClient.setQueryData(['me', result.token], result.user)
      setToken(result.token)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    },
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!mismatch) {
      change.mutate()
    }
  }

  return (
    <form className="card narrow" onSubmit={submit}>
      <h2>Change password</h2>
      <p className="muted">Signed in as {user?.username}. Other devices will be logged out.</p>
      <input type="text" value={user?.username ?? ''} autoComplete="username" readOnly hidden />
      <label>
        Current password
        <input
          type="password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
      </label>
      <label>
        New password
        <input
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          autoComplete="new-password"
          required
        />
      </label>
      <label>
        Confirm new password
        <input
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          autoComplete="new-password"
          required
        />
      </label>
      {mismatch && <p className="error">Passwords do not match.</p>}
      <ErrorText error={change.error} />
      {change.isSuccess && <p className="success">Your password has been changed.</p>}
      <button type="submit" disabled={change.isPending || mismatch}>
        Change password
      </button>
    </form>
  )
}
