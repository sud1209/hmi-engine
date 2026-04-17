import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useResearchStatus } from '@/hooks/useResearchStatus'
import { api } from '@/lib/api'

jest.mock('@/lib/api')
const mockedApi = api as jest.Mocked<typeof api>

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('useResearchStatus', () => {
  it('returns undefined data when runId is null', () => {
    const { result } = renderHook(() => useResearchStatus(null), { wrapper })
    expect(result.current.data).toBeUndefined()
    expect(mockedApi.getResearchStatus).not.toHaveBeenCalled()
  })

  it('fetches status when runId is provided', async () => {
    mockedApi.getResearchStatus.mockResolvedValue({
      run_id: 'abc', status: 'running',
    })
    const { result } = renderHook(() => useResearchStatus('abc'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.status).toBe('running')
  })

  it('stops polling when status is terminal', async () => {
    mockedApi.getResearchStatus.mockResolvedValue({
      run_id: 'abc', status: 'complete',
    })
    const { result } = renderHook(() => useResearchStatus('abc'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.status).toBe('complete')
  })
})
