import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { TERMINAL_STATUSES } from '@/lib/types'

export function useResearchStatus(runId: string | null) {
  return useQuery({
    queryKey: ['research', 'status', runId],
    queryFn: () => api.getResearchStatus(runId!),
    enabled: runId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (!status || TERMINAL_STATUSES.includes(status)) return false
      return 3_000
    },
  })
}
