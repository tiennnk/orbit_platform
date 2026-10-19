import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useMemo, useSyncExternalStore, type ReactNode } from 'react'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { AuthContext, type AuthState } from './context'
import { clearToken, getToken, setToken, subscribe } from './token'

export function AuthProvider({ children }: { children: ReactNode }) {
  const token = useSyncExternalStore(subscribe, getToken)
  const queryClient = useQueryClient()

  const me = useQuery({
    queryKey: ['me', token],
    queryFn: () => unwrap(api.GET('/api/v1/auth/me/')),
    enabled: token !== null,
    retry: false,
  })

  const login = useCallback(async (username: string, password: string) => {
    const result = await unwrap(api.POST('/api/v1/auth/login/', { body: { username, password } }))
    queryClient.clear()
    setToken(result.token)
  }, [queryClient])

  const register = useCallback(async (username: string, password: string) => {
    const result = await unwrap(api.POST('/api/v1/auth/register/', { body: { username, password } }))
    queryClient.clear()
    setToken(result.token)
  }, [queryClient])

  const logout = useCallback(async () => {
    await api.POST('/api/v1/auth/logout/').catch(() => undefined)
    clearToken()
    queryClient.clear()
  }, [queryClient])

  const value = useMemo<AuthState>(
    () => ({
      user: token ? (me.data ?? null) : null,
      loading: token !== null && me.isPending,
      login,
      register,
      logout,
    }),
    [token, me.data, me.isPending, login, register, logout],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}
