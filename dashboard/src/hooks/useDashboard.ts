import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useDashboard(market: string) {
  return useQuery({
    queryKey: ['dashboard', market],
    queryFn: () => api.getDashboard(market),
    staleTime: 60_000,
    refetchInterval: 60_000,
  })
}
