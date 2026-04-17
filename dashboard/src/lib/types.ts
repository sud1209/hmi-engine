export interface NewsItem {
  headline: string
  summary: string
  source: string
  relevance_score: 'high' | 'medium' | 'low'
}

export interface MortgageRate {
  term_years: number
  rate: number
  rate_type: string
}

export interface MarketSnapshot {
  total_listings: number
  average_median_price: number
  latest_mortgage_rate: number
  as_of_date: string
}

export interface DashboardResponse {
  kpis: Record<string, string>
  recent_news: NewsItem[]
  market_snapshot: MarketSnapshot
  mortgage_rates: MortgageRate[]
}

export interface HistorySnapshot {
  market: string
  month: string
  median_dom: number
  months_supply: number
  mortgage_rate_30yr: number
  price_per_sqft: number
  active_listings: number
  median_sale_price: number
  sales_volume: number
  new_listings: number
  yoy_active_listings: number | null
  yoy_sale_price: number | null
  yoy_sales_volume: number | null
  yoy_new_listings: number | null
}

export interface RankingRow {
  market: string
  value: number
  rank: number
}

export type ResearchStatus =
  | 'awaiting_approval'
  | 'running'
  | 'complete'
  | 'rejected'
  | 'error'

export interface ResearchRun {
  run_id: string
  status: ResearchStatus
  plan?: string[]
  result?: {
    report: { report_markdown: string }
    dashboard: { kpis: Record<string, unknown> }
    messages: unknown[]
  }
  error?: string
}

export interface NLQueryResponse {
  answer: string
  tools_used: string[]
}

export const YOY_METRICS = new Set([
  'active_listings',
  'median_sale_price',
  'sales_volume',
  'new_listings',
])

export const METRIC_LABELS: Record<string, string> = {
  active_listings: 'Active Listings',
  median_sale_price: 'Median Sale Price',
  sales_volume: 'Sales Volume',
  new_listings: 'New Listings',
  median_dom: 'Days on Market',
  months_supply: 'Months Supply',
  price_per_sqft: 'Price / sqft',
  mortgage_rate_30yr: 'Mortgage Rate',
}

export const TERMINAL_STATUSES: ResearchStatus[] = ['complete', 'rejected', 'error']
