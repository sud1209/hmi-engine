import type {
  DashboardResponse, HistorySnapshot, RankingRow,
  NLQueryResponse, ResearchRun,
} from './types'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await (options ? fetch(url, options) : fetch(url))
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, body.detail ?? body.error ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

const JSON_HEADERS = { 'Content-Type': 'application/json' }

export const api = {
  getDashboard: (market: string) =>
    request<DashboardResponse>(`/api/dashboard?market=${encodeURIComponent(market)}`),

  getHistory: (market: string, years = 5) =>
    request<HistorySnapshot[]>(`/api/history/${encodeURIComponent(market)}?years=${years}`),

  getAllHistory: () =>
    request<Record<string, HistorySnapshot[]>>('/api/history/all'),

  getRankings: (metric: string, sort: 'asc' | 'desc' = 'desc') =>
    request<RankingRow[]>(`/api/msa/rankings?metric=${encodeURIComponent(metric)}&sort=${sort}`),

  nlQuery: (query: string) =>
    request<NLQueryResponse>('/api/query', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ query }),
    }),

  startResearch: (query: string) =>
    request<ResearchRun>('/api/research', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ query }),
    }),

  getResearchStatus: (runId: string) =>
    request<ResearchRun>(`/api/research/${runId}/status`),

  approveResearch: (runId: string, approved: boolean) =>
    request<ResearchRun>(`/api/research/${runId}/approve`, {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ approved }),
    }),
}
