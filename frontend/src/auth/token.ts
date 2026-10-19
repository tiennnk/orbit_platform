const KEY = 'orbit.token'

type Listener = () => void
const listeners = new Set<Listener>()

function read(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

function persist(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(KEY, token)
    } else {
      localStorage.removeItem(KEY)
    }
  } catch (error) {
    console.warn('Could not persist auth token', error)
  }
}

let current = read()

function update(token: string | null): void {
  current = token
  persist(token)
  listeners.forEach((listener) => listener())
}

export function getToken(): string | null {
  return current
}

export function setToken(token: string): void {
  update(token)
}

export function clearToken(): void {
  update(null)
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}
