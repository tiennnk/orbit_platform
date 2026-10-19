import createClient, { type Middleware } from 'openapi-fetch'
import type { components, paths } from './schema'
import { clearToken, getToken } from '../auth/token'

export type Schemas = components['schemas']
export type Driver = Schemas['Driver']
export type Ride = Schemas['Ride']
export type User = Schemas['User']
export type NearbyDriver = Schemas['NearbyDriver']
export type Restaurant = Schemas['Restaurant']
export type RestaurantDetail = Schemas['RestaurantDetail']
export type MenuItem = Schemas['MenuItem']

const auth: Middleware = {
  onRequest({ request }) {
    const token = getToken()
    if (token && !request.url.includes('/auth/login/') && !request.url.includes('/auth/register/')) {
      request.headers.set('Authorization', `Token ${token}`)
    }
    return request
  },
  onResponse({ response }) {
    if (response.status === 401 && getToken()) {
      clearToken()
    }
    return response
  },
}

export const api = createClient<paths>({ baseUrl: '' })
api.use(auth)
