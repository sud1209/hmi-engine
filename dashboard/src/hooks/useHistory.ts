import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useHistory(market: string, years = 5) {
  return useQuery({
    queryKey: ['history', market, years],
    queryFn: () => api.getHistory(market, years),
    staleTime: 300_000,
    enabled: !!market,
  })
}
