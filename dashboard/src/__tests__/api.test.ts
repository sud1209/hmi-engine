import { ApiError, api } from '@/lib/api'

global.fetch = jest.fn()

beforeEach(() => jest.resetAllMocks())

function mockFetch(status: number, body: unknown) {
  ;(global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  })
}

describe('ApiError', () => {
  it('stores status and message', () => {
    const err = new ApiError(429, 'Rate limit exceeded')
    expect(err.status).toBe(429)
    expect(err.message).toBe('Rate limit exceeded')
    expect(err).toBeInstanceOf(Error)
  })
})

describe('api.getDashboard', () => {
  it('returns data on 200', async () => {
    const payload = { kpis: {}, recent_news: [], market_snapshot: {}, mortgage_rates: [] }
    mockFetch(200, payload)
    const result = await api.getDashboard('National')
    expect(result).toEqual(payload)
    expect(global.fetch).toHaveBeenCalledWith('/api/dashboard?market=National')
  })

  it('throws ApiError on 429', async () => {
    mockFetch(429, { detail: 'Rate limit exceeded' })
    await expect(api.getDashboard('National')).rejects.toThrow(ApiError)
  })
})

describe('api.nlQuery', () => {
  it('calls POST /api/query with body', async () => {
    mockFetch(200, { answer: 'test', tools_used: [] })
    await api.nlQuery('what is the price?')
    expect(global.fetch).toHaveBeenCalledWith('/api/query', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ query: 'what is the price?' }),
    }))
  })
})
