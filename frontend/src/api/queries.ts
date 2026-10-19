import { useQuery } from '@tanstack/react-query'
import { api } from './client'
import { ApiError, unwrap } from './errors'

async function orNull<T>(call: Promise<T>): Promise<T | null> {
  try {
    return await call
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null
    }
    throw error
  }
}

export function useCurrentRide() {
  return useQuery({
    queryKey: ['current-ride'],
    queryFn: () => orNull(unwrap(api.GET('/api/v1/rides/current/'))),
    refetchInterval: 4000,
  })
}

export function useMyDriver(enabled = true) {
  return useQuery({
    queryKey: ['my-driver'],
    queryFn: () => orNull(unwrap(api.GET('/api/v1/drivers/me/'))),
    refetchInterval: 5000,
    enabled,
  })
}

export function useCurrentOffer(enabled: boolean) {
  return useQuery({
    queryKey: ['current-offer'],
    queryFn: () => orNull(unwrap(api.GET('/api/v1/rides/offers/current/'))),
    refetchInterval: 2000,
    enabled,
  })
}
