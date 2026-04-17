import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useRankings(metric: string, sort: 'asc' | 'desc' = 'desc') {
  return useQuery({
    queryKey: ['rankings', metric, sort],
    queryFn: () => api.getRankings(metric, sort),
    staleTime: 300_000,
  })
}
