import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useAllHistory() {
  return useQuery({
    queryKey: ['history', 'all'],
    queryFn: () => api.getAllHistory(),
    staleTime: 600_000,  // 10 min — heavy request, cache aggressively
  })
}
