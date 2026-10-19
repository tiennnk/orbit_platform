import type { User } from '../api/client'

export function homePath(user: User): string {
  return user.is_staff ? '/admin' : '/ride'
}
