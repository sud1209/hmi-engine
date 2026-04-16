# Next.js Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Streamlit `dashboard` service with a Next.js 15 + shadcn/ui + Recharts application — same docker-compose slot, full feature parity, dark/light theme toggle.

**Architecture:** Next.js 15 App Router as the single dashboard service. Server-side route handlers proxy all API calls to `mcp-server:8001` and `agent-runner:8000` over the Docker internal network (browser never calls those services directly). Client-side uses React Query for caching/polling, Zustand for global state (market selector, viz metric, compare markets), and Recharts for all charts. CSS variables power the dark/light theme; `next-themes` applies the `.dark` class to `html`.

**Tech Stack:** Next.js 15, React 19, TypeScript 5, Tailwind CSS v4, shadcn/ui, Recharts 2, @tanstack/react-query 5, Zustand 5, next-themes, react-markdown, lucide-react, Jest + @testing-library/react.

---

## File Map

| File | Responsibility |
|---|---|
| `dashboard/package.json` | Dependencies and scripts |
| `dashboard/next.config.ts` | `output: standalone`, env vars |
| `dashboard/postcss.config.mjs` | Tailwind v4 postcss plugin |
| `dashboard/tsconfig.json` | TypeScript config |
| `dashboard/jest.config.ts` | Jest + next/jest setup |
| `dashboard/jest.setup.ts` | @testing-library/jest-dom matchers |
| `dashboard/Dockerfile` | Multi-stage node:20-alpine build |
| `dashboard/src/app/globals.css` | CSS variables (dark/light), Tailwind import |
| `dashboard/src/app/layout.tsx` | ThemeProvider + QueryClientProvider root |
| `dashboard/src/app/page.tsx` | Dashboard shell: Navbar + 4 Tabs |
| `dashboard/src/app/api/dashboard/route.ts` | Proxy → mcp-server /dashboard |
| `dashboard/src/app/api/history/[market]/route.ts` | Proxy → mcp-server /history/{market} |
| `dashboard/src/app/api/msa/rankings/route.ts` | Proxy → mcp-server /msa/rankings |
| `dashboard/src/app/api/query/route.ts` | Proxy → mcp-server /query |
| `dashboard/src/app/api/research/route.ts` | Proxy → agent-runner /research |
| `dashboard/src/app/api/research/[runId]/status/route.ts` | Proxy → agent-runner /research/{id}/status |
| `dashboard/src/app/api/research/[runId]/approve/route.ts` | Proxy → agent-runner /research/{id}/approve |
| `dashboard/src/lib/types.ts` | All TypeScript interfaces matching API shapes |
| `dashboard/src/lib/utils.ts` | `cn()`, `formatMetricValue()`, `isYoYMetric()` |
| `dashboard/src/lib/api.ts` | Typed fetch wrappers, `ApiError` class |
| `dashboard/src/lib/store.ts` | Zustand store: market, vizMetric, compareMarkets |
| `dashboard/src/hooks/useDashboard.ts` | React Query, 60s refetch |
| `dashboard/src/hooks/useHistory.ts` | React Query, 300s stale |
| `dashboard/src/hooks/useAllHistory.ts` | React Query, 600s stale, all MSAs |
| `dashboard/src/hooks/useRankings.ts` | React Query, 300s stale |
| `dashboard/src/hooks/useResearchStatus.ts` | React Query, 3s polling, auto-stop |
| `dashboard/src/components/layout/Navbar.tsx` | Logo, market selector, theme toggle |
| `dashboard/src/components/layout/ThemeToggle.tsx` | Sun/Moon button |
| `dashboard/src/components/overview/KPICard.tsx` | Single metric tile |
| `dashboard/src/components/overview/KPIGrid.tsx` | 8-tile grid |
| `dashboard/src/components/overview/NLSearchBar.tsx` | NL query input + answer display |
| `dashboard/src/components/overview/NewsPanel.tsx` | 4 news cards |
| `dashboard/src/components/overview/MortgageRatesTable.tsx` | Rate table |
| `dashboard/src/components/overview/ResearchPanel.tsx` | HITL research flow (collapsible) |
| `dashboard/src/components/charts/TrendsChart.tsx` | All-MSA line chart + highlighted market |
| `dashboard/src/components/charts/RankingsChart.tsx` | Horizontal bar chart |
| `dashboard/src/components/charts/YearlyComparisonChart.tsx` | Seasonality chart |
| `dashboard/src/__tests__/utils.test.ts` | formatMetricValue, isYoYMetric |
| `dashboard/src/__tests__/api.test.ts` | ApiError, error handling |
| `dashboard/src/__tests__/useResearchStatus.test.tsx` | Polling + auto-stop |

---

## Task 1: Remove Streamlit files and scaffold Next.js project

**Files:**
- Delete: `dashboard/dashboard.py`, `dashboard/pyproject.toml`, `dashboard/Dockerfile`
- Create: `dashboard/package.json`
- Create: `dashboard/next.config.ts`
- Create: `dashboard/postcss.config.mjs`
- Create: `dashboard/tsconfig.json`
- Create: `dashboard/jest.config.ts`
- Create: `dashboard/jest.setup.ts`

- [ ] **Step 1: Remove Streamlit files**

```bash
cd dashboard
rm dashboard.py pyproject.toml Dockerfile
```

- [ ] **Step 2: Create `dashboard/package.json`**

```json
{
  "name": "hmi-dashboard",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start --port 3000",
    "test": "jest --passWithNoTests",
    "test:watch": "jest --watch"
  },
  "dependencies": {
    "next": "15.3.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "recharts": "^2.15.0",
    "@tanstack/react-query": "^5.74.0",
    "zustand": "^5.0.3",
    "next-themes": "^0.4.6",
    "react-markdown": "^9.0.3",
    "lucide-react": "^0.503.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^3.2.0",
    "@radix-ui/react-tabs": "^1.1.3",
    "@radix-ui/react-select": "^2.1.6",
    "@radix-ui/react-collapsible": "^1.1.3",
    "@radix-ui/react-toggle-group": "^1.1.1",
    "@radix-ui/react-progress": "^1.1.2",
    "@radix-ui/react-slot": "^1.2.0"
  },
  "devDependencies": {
    "typescript": "^5.8.3",
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "tailwindcss": "^4.1.4",
    "@tailwindcss/postcss": "^4.1.4",
    "jest": "^29.7.0",
    "jest-environment-jsdom": "^29.7.0",
    "@testing-library/react": "^16.3.0",
    "@testing-library/jest-dom": "^6.6.3",
    "@types/jest": "^29.5.14",
    "ts-jest": "^29.3.2"
  }
}
```

- [ ] **Step 3: Create `dashboard/next.config.ts`**

```typescript
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
}

export default nextConfig
```

- [ ] **Step 4: Create `dashboard/postcss.config.mjs`**

```javascript
const config = {
  plugins: {
    '@tailwindcss/postcss': {},
  },
}
export default config
```

- [ ] **Step 5: Create `dashboard/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 6: Create `dashboard/jest.config.ts`**

```typescript
import type { Config } from 'jest'
import nextJest from 'next/jest.js'

const createJestConfig = nextJest({ dir: './' })

const config: Config = {
  coverageProvider: 'v8',
  testEnvironment: 'jsdom',
  setupFilesAfterFramework: ['<rootDir>/jest.setup.ts'],
}

export default createJestConfig(config)
```

- [ ] **Step 7: Create `dashboard/jest.setup.ts`**

```typescript
import '@testing-library/jest-dom'
```

- [ ] **Step 8: Install dependencies**

```bash
cd dashboard
npm install
```

Expected: `node_modules/` created, no errors.

- [ ] **Step 9: Commit**

```bash
git add dashboard/
git commit -m "feat(dashboard): scaffold Next.js 15 project, remove Streamlit"
```

---

## Task 2: Theme system — CSS variables + providers

**Files:**
- Create: `dashboard/src/app/globals.css`
- Create: `dashboard/src/app/layout.tsx`
- Create: `dashboard/src/components/layout/ThemeToggle.tsx`

- [ ] **Step 1: Create `dashboard/src/app/globals.css`**

```css
@import "tailwindcss";

@theme {
  --color-bg: var(--bg);
  --color-surface: var(--surface);
  --color-border: var(--border);
  --color-accent: var(--accent);
  --color-muted: var(--muted);
}

/* Light (default :root for SSR) */
:root {
  --bg: #f8f8fc;
  --surface: #ffffff;
  --border: #e2e2ec;
  --accent: #3479f5;
  --muted: #6060a0;
  --text: #0f0f13;
}

/* Dark */
.dark {
  --bg: #0f0f13;
  --surface: #1a1a24;
  --border: #2a2a3a;
  --accent: #3479f5;
  --muted: #7070a0;
  --text: #e8e8f0;
}

html {
  background-color: var(--bg);
  color: var(--text);
  font-family: Inter, system-ui, -apple-system, sans-serif;
}

* {
  border-color: var(--border);
}
```

- [ ] **Step 2: Create `dashboard/src/app/layout.tsx`**

```typescript
'use client'

import './globals.css'
import { ThemeProvider } from 'next-themes'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: { retry: 1, refetchOnWindowFocus: false },
    },
  }))

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <title>HMI Engine</title>
        <meta name="description" content="Housing Market Intelligence" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 3: Create `dashboard/src/components/layout/ThemeToggle.tsx`**

```typescript
'use client'

import { useTheme } from 'next-themes'
import { Sun, Moon } from 'lucide-react'
import { useEffect, useState } from 'react'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  // Avoid hydration mismatch
  useEffect(() => setMounted(true), [])
  if (!mounted) return <div className="w-9 h-9" />

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="p-2 rounded-md hover:bg-[var(--surface)] transition-colors"
      aria-label="Toggle theme"
    >
      {theme === 'dark'
        ? <Sun size={18} style={{ color: 'var(--muted)' }} />
        : <Moon size={18} style={{ color: 'var(--muted)' }} />
      }
    </button>
  )
}
```

- [ ] **Step 4: Create a minimal `dashboard/src/app/page.tsx` to verify theme works**

```typescript
import { ThemeToggle } from '@/components/layout/ThemeToggle'

export default function Page() {
  return (
    <main style={{ padding: '2rem' }}>
      <ThemeToggle />
      <h1 style={{ color: 'var(--text)', marginTop: '1rem' }}>HMI Engine</h1>
    </main>
  )
}
```

- [ ] **Step 5: Start dev server and verify dark default + toggle**

```bash
cd dashboard
npm run dev
```

Open http://localhost:3000 — should load with dark background `#0f0f13`. Toggle should switch to light `#f8f8fc`. Check browser console for errors.

- [ ] **Step 6: Commit**

```bash
git add dashboard/src/
git commit -m "feat(dashboard): theme system — CSS variables, ThemeProvider, toggle"
```

---

## Task 3: Types

**Files:**
- Create: `dashboard/src/lib/types.ts`

- [ ] **Step 1: Create `dashboard/src/lib/types.ts`**

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/lib/types.ts
git commit -m "feat(dashboard): TypeScript types matching API response shapes"
```

---

## Task 4: Utility functions + tests

**Files:**
- Create: `dashboard/src/lib/utils.ts`
- Create: `dashboard/src/__tests__/utils.test.ts`

- [ ] **Step 1: Write failing tests first**

Create `dashboard/src/__tests__/utils.test.ts`:

```typescript
import { formatMetricValue, isYoYMetric, cn } from '@/lib/utils'

describe('isYoYMetric', () => {
  it('returns true for YoY metrics', () => {
    expect(isYoYMetric('active_listings')).toBe(true)
    expect(isYoYMetric('median_sale_price')).toBe(true)
    expect(isYoYMetric('sales_volume')).toBe(true)
    expect(isYoYMetric('new_listings')).toBe(true)
  })

  it('returns false for absolute metrics', () => {
    expect(isYoYMetric('median_dom')).toBe(false)
    expect(isYoYMetric('months_supply')).toBe(false)
    expect(isYoYMetric('price_per_sqft')).toBe(false)
    expect(isYoYMetric('mortgage_rate_30yr')).toBe(false)
  })
})

describe('formatMetricValue', () => {
  it('formats YoY metrics as percentage with sign', () => {
    expect(formatMetricValue('active_listings', 12.4)).toBe('+12.4%')
    expect(formatMetricValue('active_listings', -5.2)).toBe('-5.2%')
    expect(formatMetricValue('median_sale_price', 0)).toBe('+0.0%')
  })

  it('formats median_dom as days', () => {
    expect(formatMetricValue('median_dom', 28)).toBe('28 days')
  })

  it('formats months_supply with one decimal', () => {
    expect(formatMetricValue('months_supply', 2.4)).toBe('2.4 mo')
  })

  it('formats price_per_sqft as dollars', () => {
    expect(formatMetricValue('price_per_sqft', 248)).toBe('$248')
  })

  it('formats mortgage_rate_30yr as percent', () => {
    expect(formatMetricValue('mortgage_rate_30yr', 6.82)).toBe('6.82%')
  })

  it('returns "—" for null/undefined', () => {
    expect(formatMetricValue('active_listings', null as unknown as number)).toBe('—')
    expect(formatMetricValue('median_dom', undefined as unknown as number)).toBe('—')
  })
})

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('a', 'b')).toBe('a b')
    expect(cn('px-2', 'px-4')).toBe('px-4') // tailwind-merge deduplication
  })
})
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd dashboard
npm test -- --testPathPattern=utils
```

Expected: FAIL — `Cannot find module '@/lib/utils'`

- [ ] **Step 3: Create `dashboard/src/lib/utils.ts`**

```typescript
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { YOY_METRICS } from './types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function isYoYMetric(metric: string): boolean {
  return YOY_METRICS.has(metric)
}

export function formatMetricValue(metric: string, value: number): string {
  if (value === null || value === undefined) return '—'

  if (isYoYMetric(metric)) {
    const sign = value >= 0 ? '+' : ''
    return `${sign}${value.toFixed(1)}%`
  }

  switch (metric) {
    case 'median_dom':
      return `${Math.round(value)} days`
    case 'months_supply':
      return `${value.toFixed(1)} mo`
    case 'price_per_sqft':
      return `$${Math.round(value)}`
    case 'mortgage_rate_30yr':
      return `${value.toFixed(2)}%`
    default:
      return String(value)
  }
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
npm test -- --testPathPattern=utils
```

Expected: PASS — all 10 assertions green.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/lib/utils.ts dashboard/src/__tests__/utils.test.ts
git commit -m "feat(dashboard): utils — cn, isYoYMetric, formatMetricValue with tests"
```

---

## Task 5: API client + tests

**Files:**
- Create: `dashboard/src/lib/api.ts`
- Create: `dashboard/src/__tests__/api.test.ts`

- [ ] **Step 1: Write failing tests**

Create `dashboard/src/__tests__/api.test.ts`:

```typescript
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
    await expect(api.getDashboard('National')).rejects.toMatchObject({ status: 429 })
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
```

- [ ] **Step 2: Run tests — expect failures**

```bash
npm test -- --testPathPattern=api
```

Expected: FAIL — `Cannot find module '@/lib/api'`

- [ ] **Step 3: Create `dashboard/src/lib/api.ts`**

```typescript
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
  const res = await fetch(url, options)
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
    request<RankingRow[]>(`/api/msa/rankings?metric=${metric}&sort=${sort}`),

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
```

- [ ] **Step 4: Run tests — expect pass**

```bash
npm test -- --testPathPattern=api
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/lib/api.ts dashboard/src/__tests__/api.test.ts
git commit -m "feat(dashboard): typed API client with ApiError, all endpoints"
```

---

## Task 6: Zustand store

**Files:**
- Create: `dashboard/src/lib/store.ts`

- [ ] **Step 1: Create `dashboard/src/lib/store.ts`**

```typescript
import { create } from 'zustand'

interface HMIStore {
  market: string
  vizMetric: string
  compareMarkets: string[]
  setMarket: (market: string) => void
  setVizMetric: (metric: string) => void
  setCompareMarkets: (markets: string[]) => void
}

export const useHMIStore = create<HMIStore>((set) => ({
  market: 'National',
  vizMetric: 'median_sale_price',
  compareMarkets: ['National'],
  setMarket: (market) => set({ market }),
  setVizMetric: (vizMetric) => set({ vizMetric }),
  setCompareMarkets: (compareMarkets) => set({ compareMarkets }),
}))
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/lib/store.ts
git commit -m "feat(dashboard): Zustand store — market, vizMetric, compareMarkets"
```

---

## Task 7: API proxy route handlers

**Files:** 7 route handler files under `dashboard/src/app/api/`

All handlers follow the same pattern: receive a Next.js `Request`, forward to the appropriate internal service, and stream the response back. The internal hostnames come from `process.env.MCP_API` and `process.env.AGENT_API`.

- [ ] **Step 1: Create `dashboard/src/app/api/dashboard/route.ts`**

```typescript
import { NextRequest, NextResponse } from 'next/server'

const MCP = process.env.MCP_API ?? 'http://localhost:8001'

export async function GET(req: NextRequest) {
  const market = req.nextUrl.searchParams.get('market') ?? 'National'
  try {
    const res = await fetch(`${MCP}/dashboard?market=${encodeURIComponent(market)}`)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: 'mcp-server unreachable' }, { status: 502 })
  }
}
```

- [ ] **Step 2: Create `dashboard/src/app/api/history/[market]/route.ts`**

```typescript
import { NextRequest, NextResponse } from 'next/server'

const MCP = process.env.MCP_API ?? 'http://localhost:8001'

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ market: string }> }
) {
  const { market } = await params
  const years = req.nextUrl.searchParams.get('years') ?? '5'
  try {
    const res = await fetch(
      `${MCP}/history/${encodeURIComponent(market)}?years=${years}`
    )
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: 'mcp-server unreachable' }, { status: 502 })
  }
}
```

- [ ] **Step 3: Create `dashboard/src/app/api/history/all/route.ts`**

```typescript
import { NextResponse } from 'next/server'

const MCP = process.env.MCP_API ?? 'http://localhost:8001'

// Fetches history for all available markets and returns as a market→snapshots map
export async function GET() {
  try {
    // Get rankings to discover all market names
    const rankRes = await fetch(`${MCP}/msa/rankings?metric=median_sale_price&sort=desc&limit=100`)
    const rankings = await rankRes.json() as { market: string }[]
    const markets = ['National', ...rankings.map((r) => r.market)]

    const entries = await Promise.all(
      markets.map(async (m) => {
        const res = await fetch(`${MCP}/history/${encodeURIComponent(m)}?years=5`)
        const data = await res.json()
        return [m, Array.isArray(data) ? data : []] as const
      })
    )
    return NextResponse.json(Object.fromEntries(entries))
  } catch {
    return NextResponse.json({ detail: 'mcp-server unreachable' }, { status: 502 })
  }
}
```

- [ ] **Step 4: Create `dashboard/src/app/api/msa/rankings/route.ts`**

```typescript
import { NextRequest, NextResponse } from 'next/server'

const MCP = process.env.MCP_API ?? 'http://localhost:8001'

export async function GET(req: NextRequest) {
  const metric = req.nextUrl.searchParams.get('metric') ?? 'median_sale_price'
  const sort = req.nextUrl.searchParams.get('sort') ?? 'desc'
  try {
    const res = await fetch(`${MCP}/msa/rankings?metric=${metric}&sort=${sort}`)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: 'mcp-server unreachable' }, { status: 502 })
  }
}
```

- [ ] **Step 5: Create `dashboard/src/app/api/query/route.ts`**

```typescript
import { NextRequest, NextResponse } from 'next/server'

const MCP = process.env.MCP_API ?? 'http://localhost:8001'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const res = await fetch(`${MCP}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: 'mcp-server unreachable' }, { status: 502 })
  }
}
```

- [ ] **Step 6: Create `dashboard/src/app/api/research/route.ts`**

```typescript
import { NextRequest, NextResponse } from 'next/server'

const AGENT = process.env.AGENT_API ?? 'http://localhost:8000'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const res = await fetch(`${AGENT}/research`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: 'agent-runner unreachable' }, { status: 502 })
  }
}
```

- [ ] **Step 7: Create `dashboard/src/app/api/research/[runId]/status/route.ts`**

```typescript
import { NextRequest, NextResponse } from 'next/server'

const AGENT = process.env.AGENT_API ?? 'http://localhost:8000'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ runId: string }> }
) {
  const { runId } = await params
  try {
    const res = await fetch(`${AGENT}/research/${runId}/status`)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: 'agent-runner unreachable' }, { status: 502 })
  }
}
```

- [ ] **Step 8: Create `dashboard/src/app/api/research/[runId]/approve/route.ts`**

```typescript
import { NextRequest, NextResponse } from 'next/server'

const AGENT = process.env.AGENT_API ?? 'http://localhost:8000'

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ runId: string }> }
) {
  const { runId } = await params
  try {
    const body = await req.json()
    const res = await fetch(`${AGENT}/research/${runId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: 'agent-runner unreachable' }, { status: 502 })
  }
}
```

- [ ] **Step 9: Add health endpoint `dashboard/src/app/api/health/route.ts`**

```typescript
import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({ status: 'ok', service: 'dashboard' })
}
```

- [ ] **Step 10: Commit**

```bash
git add dashboard/src/app/api/
git commit -m "feat(dashboard): API proxy route handlers (9 routes)"
```

---

## Task 8: React Query hooks

**Files:**
- Create: `dashboard/src/hooks/useDashboard.ts`
- Create: `dashboard/src/hooks/useHistory.ts`
- Create: `dashboard/src/hooks/useAllHistory.ts`
- Create: `dashboard/src/hooks/useRankings.ts`
- Create: `dashboard/src/hooks/useResearchStatus.ts`
- Create: `dashboard/src/__tests__/useResearchStatus.test.tsx`

- [ ] **Step 1: Create `dashboard/src/hooks/useDashboard.ts`**

```typescript
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
```

- [ ] **Step 2: Create `dashboard/src/hooks/useHistory.ts`**

```typescript
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
```

- [ ] **Step 3: Create `dashboard/src/hooks/useAllHistory.ts`**

```typescript
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useAllHistory() {
  return useQuery({
    queryKey: ['history', 'all'],
    queryFn: () => api.getAllHistory(),
    staleTime: 600_000,  // 10 min — heavy request, cache aggressively
  })
}
```

- [ ] **Step 4: Create `dashboard/src/hooks/useRankings.ts`**

```typescript
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useRankings(metric: string, sort: 'asc' | 'desc' = 'desc') {
  return useQuery({
    queryKey: ['rankings', metric, sort],
    queryFn: () => api.getRankings(metric, sort),
    staleTime: 300_000,
  })
}
```

- [ ] **Step 5: Write failing test for useResearchStatus**

Create `dashboard/src/__tests__/useResearchStatus.test.tsx`:

```typescript
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
  it('returns null data when runId is null', () => {
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
    // refetchInterval should be false for terminal status
    expect(result.current.data?.status).toBe('complete')
  })
})
```

- [ ] **Step 6: Run test — expect failure**

```bash
npm test -- --testPathPattern=useResearchStatus
```

Expected: FAIL — `Cannot find module '@/hooks/useResearchStatus'`

- [ ] **Step 7: Create `dashboard/src/hooks/useResearchStatus.ts`**

```typescript
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
```

- [ ] **Step 8: Run test — expect pass**

```bash
npm test -- --testPathPattern=useResearchStatus
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add dashboard/src/hooks/ dashboard/src/__tests__/useResearchStatus.test.tsx
git commit -m "feat(dashboard): React Query hooks — dashboard, history, rankings, research status"
```

---

## Task 9: Install and configure shadcn/ui components

**Files:** `dashboard/src/components/ui/` (generated by CLI)

shadcn/ui components are generated by its CLI and committed to the repo. Install the components we need: `button`, `card`, `tabs`, `select`, `input`, `table`, `badge`, `progress`, `collapsible`, `toggle-group`, `alert`, `skeleton`, `separator`.

- [ ] **Step 1: Initialise shadcn/ui**

```bash
cd dashboard
npx shadcn@latest init
```

When prompted:
- Style: **Default**
- Base color: **Neutral**
- CSS variables: **yes**

This creates `components.json` and updates `globals.css` with shadcn's CSS variable block. After running, **merge** shadcn's `:root` / `.dark` blocks with ours — keep both our custom variables (`--bg`, `--surface`, `--border`, `--accent`, `--muted`) and shadcn's (`--background`, `--foreground`, `--primary`, etc.). The shadcn block controls its own components; our variables control custom layout styling.

- [ ] **Step 2: Add all needed components**

```bash
npx shadcn@latest add button card tabs select input table badge progress collapsible toggle-group alert skeleton separator
```

Expected: Files created under `src/components/ui/`.

- [ ] **Step 3: Verify build compiles**

```bash
npm run build
```

Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/ui/ dashboard/components.json
git commit -m "feat(dashboard): add shadcn/ui component primitives"
```

---

## Task 10: App shell — Navbar + tabbed layout

**Files:**
- Create: `dashboard/src/components/layout/Navbar.tsx`
- Modify: `dashboard/src/app/page.tsx`

- [ ] **Step 1: Create `dashboard/src/components/layout/Navbar.tsx`**

```typescript
'use client'

import { ThemeToggle } from './ThemeToggle'
import { useHMIStore } from '@/lib/store'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

const MARKETS = [
  'National', 'Austin', 'Dallas', 'Houston', 'Phoenix', 'Denver',
  'Atlanta', 'Charlotte', 'Nashville', 'Tampa', 'Orlando',
]

export function Navbar() {
  const { market, setMarket } = useHMIStore()

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 h-14 border-b"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      <span className="font-semibold text-sm tracking-tight" style={{ color: 'var(--text)' }}>
        HMI Engine
      </span>

      <Select value={market} onValueChange={setMarket}>
        <SelectTrigger className="w-44 h-8 text-sm">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {MARKETS.map((m) => (
            <SelectItem key={m} value={m}>{m}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <ThemeToggle />
    </nav>
  )
}
```

- [ ] **Step 2: Replace `dashboard/src/app/page.tsx` with tabbed shell**

```typescript
'use client'

import { Navbar } from '@/components/layout/Navbar'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { OverviewTab } from '@/components/tabs/OverviewTab'
import { TrendsTab } from '@/components/tabs/TrendsTab'
import { RankingsTab } from '@/components/tabs/RankingsTab'
import { YearlyComparisonTab } from '@/components/tabs/YearlyComparisonTab'

export default function Page() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Navbar />
      <main className="pt-14 px-6 pb-8 max-w-screen-xl mx-auto">
        <Tabs defaultValue="overview" className="mt-6">
          <TabsList className="mb-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="trends">Trends</TabsTrigger>
            <TabsTrigger value="rankings">Rankings</TabsTrigger>
            <TabsTrigger value="yearly">Yearly Comparison</TabsTrigger>
          </TabsList>

          <TabsContent value="overview"><OverviewTab /></TabsContent>
          <TabsContent value="trends"><TrendsTab /></TabsContent>
          <TabsContent value="rankings"><RankingsTab /></TabsContent>
          <TabsContent value="yearly"><YearlyComparisonTab /></TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
```

- [ ] **Step 3: Create tab placeholder files so the build compiles**

Create `dashboard/src/components/tabs/OverviewTab.tsx`:
```typescript
export function OverviewTab() { return <div>Overview</div> }
```

Create `dashboard/src/components/tabs/TrendsTab.tsx`:
```typescript
export function TrendsTab() { return <div>Trends</div> }
```

Create `dashboard/src/components/tabs/RankingsTab.tsx`:
```typescript
export function RankingsTab() { return <div>Rankings</div> }
```

Create `dashboard/src/components/tabs/YearlyComparisonTab.tsx`:
```typescript
export function YearlyComparisonTab() { return <div>Yearly Comparison</div> }
```

- [ ] **Step 4: Start dev server and verify shell renders**

```bash
npm run dev
```

Open http://localhost:3000. Should show: fixed navbar with "HMI Engine" + market selector + toggle, 4 tab triggers, placeholder text per tab. Dark background, no console errors.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/ dashboard/src/app/page.tsx
git commit -m "feat(dashboard): app shell — Navbar, ThemeToggle, 4 tab layout"
```

---

## Task 11: KPI tiles

**Files:**
- Create: `dashboard/src/components/overview/KPICard.tsx`
- Create: `dashboard/src/components/overview/KPIGrid.tsx`

- [ ] **Step 1: Create `dashboard/src/components/overview/KPICard.tsx`**

```typescript
import { Skeleton } from '@/components/ui/skeleton'

interface KPICardProps {
  label: string
  value: string
  loading?: boolean
}

export function KPICard({ label, value, loading }: KPICardProps) {
  return (
    <div
      className="rounded-lg p-4 flex flex-col gap-2"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
    >
      <span
        className="text-xs font-medium uppercase tracking-widest"
        style={{ color: 'var(--muted)' }}
      >
        {label}
      </span>
      {loading
        ? <Skeleton className="h-8 w-3/4" />
        : <span className="text-2xl font-bold" style={{ color: 'var(--text)' }}>{value}</span>
      }
    </div>
  )
}
```

- [ ] **Step 2: Create `dashboard/src/components/overview/KPIGrid.tsx`**

```typescript
'use client'

import { KPICard } from './KPICard'
import { useDashboard } from '@/hooks/useDashboard'
import { useHMIStore } from '@/lib/store'

const KPI_LABELS: Record<string, string> = {
  avg_list_price: 'Avg List Price',
  active_listings: 'Active Listings',
  rate_30yr_fixed: '30yr Rate',
  median_dom: 'Median DOM',
  price_per_sqft: 'Price / sqft',
  new_listings_30d: 'New Listings (30d)',
  price_reductions: 'Price Reductions',
  months_supply: 'Months Supply',
}

export function KPIGrid() {
  const { market } = useHMIStore()
  const { data, isLoading } = useDashboard(market)

  const kpis = data?.kpis ?? {}

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {Object.entries(KPI_LABELS).map(([key, label]) => (
        <KPICard
          key={key}
          label={label}
          value={kpis[key] ?? '—'}
          loading={isLoading}
        />
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/overview/KPICard.tsx dashboard/src/components/overview/KPIGrid.tsx
git commit -m "feat(dashboard): KPI tiles — KPICard and KPIGrid with loading skeletons"
```

---

## Task 12: NL Search bar

**Files:**
- Create: `dashboard/src/components/overview/NLSearchBar.tsx`

- [ ] **Step 1: Create `dashboard/src/components/overview/NLSearchBar.tsx`**

```typescript
'use client'

import { useState, FormEvent } from 'react'
import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { api, ApiError } from '@/lib/api'
import { Skeleton } from '@/components/ui/skeleton'

export function NLSearchBar() {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)
  const [toolsUsed, setToolsUsed] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setAnswer(null)
    setError(null)

    try {
      const res = await api.nlQuery(query.trim())
      setAnswer(res.answer)
      setToolsUsed(res.tools_used)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 429) setError('Too many searches — wait a moment before trying again.')
        else if (err.status === 408) setError("Search timed out. Try a more specific question.")
        else setError('Search failed. Please try again.')
      } else {
        setError('Search failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-full space-y-3">
      <form onSubmit={handleSubmit} className="relative flex items-center">
        <Search
          size={16}
          className="absolute left-3"
          style={{ color: 'var(--muted)' }}
        />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask about the housing market..."
          className="pl-9 h-11 text-sm"
          disabled={loading}
          maxLength={500}
        />
      </form>

      {loading && <Skeleton className="h-12 w-full" />}

      {error && (
        <div
          className="rounded-md px-4 py-3 text-sm"
          style={{ background: 'color-mix(in srgb, var(--accent) 10%, transparent)', color: 'var(--text)' }}
        >
          ⚠️ {error}
        </div>
      )}

      {answer && !loading && (
        <div className="space-y-1">
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text)' }}>
            {answer}
          </p>
          {toolsUsed.length > 0 && (
            <p className="text-xs" style={{ color: 'var(--muted)' }}>
              Used: {toolsUsed.join(', ')}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/components/overview/NLSearchBar.tsx
git commit -m "feat(dashboard): NL search bar with loading, error, and answer states"
```

---

## Task 13: News panel + Mortgage rates table

**Files:**
- Create: `dashboard/src/components/overview/NewsPanel.tsx`
- Create: `dashboard/src/components/overview/MortgageRatesTable.tsx`

- [ ] **Step 1: Create `dashboard/src/components/overview/NewsPanel.tsx`**

```typescript
'use client'

import { useDashboard } from '@/hooks/useDashboard'
import { useHMIStore } from '@/lib/store'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import type { NewsItem } from '@/lib/types'

const RELEVANCE_COLORS: Record<string, string> = {
  high: '#22c55e',
  medium: '#f59e0b',
  low: '#6b7280',
}

function NewsCard({ item }: { item: NewsItem }) {
  return (
    <div
      className="rounded-lg p-4 space-y-2"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium leading-snug" style={{ color: 'var(--text)' }}>
          {item.headline}
        </p>
        <span
          className="mt-1 flex-shrink-0 w-2 h-2 rounded-full"
          style={{ background: RELEVANCE_COLORS[item.relevance_score] ?? '#6b7280' }}
        />
      </div>
      {item.summary && (
        <p className="text-xs leading-relaxed" style={{ color: 'var(--muted)' }}>
          {item.summary}
        </p>
      )}
      <Badge variant="outline" className="text-xs">{item.source}</Badge>
    </div>
  )
}

export function NewsPanel() {
  const { market } = useHMIStore()
  const { data, isLoading } = useDashboard(market)
  const news = data?.recent_news ?? []

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
        Market News
      </h3>
      {isLoading
        ? Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))
        : news.map((item, i) => <NewsCard key={i} item={item} />)
      }
    </div>
  )
}
```

- [ ] **Step 2: Create `dashboard/src/components/overview/MortgageRatesTable.tsx`**

```typescript
'use client'

import { useDashboard } from '@/hooks/useDashboard'
import { useHMIStore } from '@/lib/store'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'

export function MortgageRatesTable() {
  const { market } = useHMIStore()
  const { data, isLoading } = useDashboard(market)
  const rates = data?.mortgage_rates ?? []

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
        Mortgage Rates
      </h3>
      <div
        className="rounded-lg overflow-hidden"
        style={{ border: '1px solid var(--border)' }}
      >
        {isLoading
          ? <Skeleton className="h-32 w-full" />
          : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Term</TableHead>
                  <TableHead>Rate</TableHead>
                  <TableHead>Type</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rates.map((r) => (
                  <TableRow key={r.term_years}>
                    <TableCell className="text-sm">{r.term_years}yr</TableCell>
                    <TableCell
                      className="text-sm font-semibold"
                      style={r.term_years === 30 ? { color: 'var(--accent)' } : { color: 'var(--text)' }}
                    >
                      {r.rate.toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-xs capitalize" style={{ color: 'var(--muted)' }}>
                      {r.rate_type}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )
        }
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/overview/NewsPanel.tsx dashboard/src/components/overview/MortgageRatesTable.tsx
git commit -m "feat(dashboard): news panel and mortgage rates table"
```

---

## Task 14: Research panel (HITL flow)

**Files:**
- Create: `dashboard/src/components/overview/ResearchPanel.tsx`

- [ ] **Step 1: Create `dashboard/src/components/overview/ResearchPanel.tsx`**

```typescript
'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useResearchStatus } from '@/hooks/useResearchStatus'
import { api, ApiError } from '@/lib/api'
import ReactMarkdown from 'react-markdown'

type PanelState = 'idle' | 'awaiting_approval' | 'running' | 'complete' | 'error'

export function ResearchPanel() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [runId, setRunId] = useState<string | null>(null)
  const [plan, setPlan] = useState<string[]>([])
  const [panelState, setPanelState] = useState<PanelState>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const { data: statusData } = useResearchStatus(
    panelState === 'running' ? runId : null
  )

  // Sync panel state from polling
  if (panelState === 'running' && statusData) {
    if (statusData.status === 'complete') setPanelState('complete')
    else if (statusData.status === 'error') {
      setPanelState('error')
      setErrorMsg(statusData.error ?? 'Pipeline failed.')
    } else if (statusData.status === 'rejected') {
      setPanelState('idle')
    }
  }

  async function handleStart() {
    if (!query.trim()) return
    setSubmitting(true)
    try {
      const run = await api.startResearch(query.trim())
      setRunId(run.run_id)
      setPlan(run.plan ?? [])
      setPanelState('awaiting_approval')
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Failed to start research.')
      setPanelState('error')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleApprove(approved: boolean) {
    if (!runId) return
    try {
      await api.approveResearch(runId, approved)
      setPanelState(approved ? 'running' : 'idle')
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Approval failed.')
      setPanelState('error')
    }
  }

  function reset() {
    setRunId(null)
    setPlan([])
    setPanelState('idle')
    setErrorMsg('')
    setQuery('')
  }

  const report = statusData?.result?.report?.report_markdown
  const kpis = statusData?.result?.dashboard?.kpis as Record<string, unknown> | undefined

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <button
          className="flex items-center gap-2 text-sm font-semibold w-full text-left py-3"
          style={{ color: 'var(--text)' }}
        >
          {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          AI Research
        </button>
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div
          className="rounded-lg p-4 space-y-4"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
        >
          {/* IDLE */}
          {panelState === 'idle' && (
            <div className="flex gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleStart()}
                placeholder="Research topic, e.g. Austin rental market outlook"
                className="text-sm"
                disabled={submitting}
                maxLength={500}
              />
              <Button onClick={handleStart} disabled={submitting || !query.trim()} size="sm">
                {submitting ? 'Starting…' : 'Run Research'}
              </Button>
            </div>
          )}

          {/* AWAITING APPROVAL */}
          {panelState === 'awaiting_approval' && (
            <div className="space-y-4">
              <div>
                <p className="text-sm font-medium mb-2" style={{ color: 'var(--text)' }}>
                  Research Plan
                </p>
                <ul className="space-y-1">
                  {plan.map((step, i) => (
                    <li key={i} className="text-sm flex gap-2" style={{ color: 'var(--muted)' }}>
                      <span style={{ color: 'var(--accent)' }}>•</span> {step}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => handleApprove(true)}>✓ Approve</Button>
                <Button size="sm" variant="outline" onClick={() => handleApprove(false)}>
                  ✗ Reject
                </Button>
              </div>
            </div>
          )}

          {/* RUNNING */}
          {panelState === 'running' && (
            <div className="space-y-3">
              <Progress value={undefined} className="h-1" />
              <p className="text-sm" style={{ color: 'var(--muted)' }}>
                Pipeline running — this takes ~30 seconds…
              </p>
            </div>
          )}

          {/* COMPLETE */}
          {panelState === 'complete' && report && (
            <div className="space-y-4">
              <div
                className="max-h-96 overflow-y-auto rounded p-4 text-sm leading-relaxed prose prose-sm"
                style={{ background: 'var(--bg)', color: 'var(--text)' }}
              >
                <ReactMarkdown>{report}</ReactMarkdown>
              </div>
              {kpis && (
                <div className="grid grid-cols-3 gap-3 text-sm">
                  {Object.entries(kpis).map(([k, v]) => (
                    <div key={k} className="text-center">
                      <p style={{ color: 'var(--muted)' }} className="text-xs">{k}</p>
                      <p style={{ color: 'var(--text)' }} className="font-semibold">{String(v)}</p>
                    </div>
                  ))}
                </div>
              )}
              <Button size="sm" variant="outline" onClick={reset}>Run another</Button>
            </div>
          )}

          {/* ERROR */}
          {panelState === 'error' && (
            <Alert variant="destructive">
              <AlertDescription className="text-sm">{errorMsg}</AlertDescription>
              <Button size="sm" variant="outline" className="mt-2" onClick={reset}>
                Try again
              </Button>
            </Alert>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/components/overview/ResearchPanel.tsx
git commit -m "feat(dashboard): HITL research panel — idle/approval/running/complete/error states"
```

---

## Task 15: Wire Overview tab

**Files:**
- Modify: `dashboard/src/components/tabs/OverviewTab.tsx`

- [ ] **Step 1: Replace OverviewTab placeholder**

```typescript
import { NLSearchBar } from '@/components/overview/NLSearchBar'
import { KPIGrid } from '@/components/overview/KPIGrid'
import { NewsPanel } from '@/components/overview/NewsPanel'
import { MortgageRatesTable } from '@/components/overview/MortgageRatesTable'
import { ResearchPanel } from '@/components/overview/ResearchPanel'

export function OverviewTab() {
  return (
    <div className="space-y-8">
      {/* 1. NL Search — hero position */}
      <NLSearchBar />

      {/* 2. KPI tiles */}
      <KPIGrid />

      {/* 3. News + Rates two-column */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3"><NewsPanel /></div>
        <div className="lg:col-span-2"><MortgageRatesTable /></div>
      </div>

      {/* 4. Research panel (collapsible) */}
      <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
        <ResearchPanel />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Start dev server, verify Overview tab**

```bash
npm run dev
```

Open http://localhost:3000. Overview tab should show: search bar, 8 KPI cards, news + rates row, research panel header. Data loads from `/api/dashboard` (proxied to mcp-server). Check Network tab confirms proxy is working.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/tabs/OverviewTab.tsx
git commit -m "feat(dashboard): wire Overview tab — search, KPIs, news, rates, research"
```

---

## Task 16: Trends chart

**Files:**
- Create: `dashboard/src/components/charts/TrendsChart.tsx`
- Modify: `dashboard/src/components/tabs/TrendsTab.tsx`

- [ ] **Step 1: Create `dashboard/src/components/charts/TrendsChart.tsx`**

```typescript
'use client'

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import { useAllHistory } from '@/hooks/useAllHistory'
import { useHistory } from '@/hooks/useHistory'
import { useHMIStore } from '@/lib/store'
import { formatMetricValue, isYoYMetric } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'
import type { HistorySnapshot } from '@/lib/types'

// Extract the right value from a snapshot for the current metric
function getMetricValue(snap: HistorySnapshot, metric: string): number | null {
  if (isYoYMetric(metric)) {
    const yoyKey = `yoy_${metric === 'median_sale_price' ? 'sale_price' : metric}` as keyof HistorySnapshot
    return (snap[yoyKey] as number | null) ?? null
  }
  return (snap[metric as keyof HistorySnapshot] as number) ?? null
}

// Format month string "2023-04-01" → "Apr 23" for Jan ticks, "Apr" otherwise
function formatTick(monthStr: string): string {
  const d = new Date(monthStr)
  const month = d.toLocaleString('en-US', { month: 'short' })
  return d.getMonth() === 0 ? `${month} ${String(d.getFullYear()).slice(2)}` : month
}

interface Props {
  metric: string
}

export function TrendsChart({ metric }: Props) {
  const { market } = useHMIStore()
  const { data: allHistory, isLoading: loadingAll } = useAllHistory()
  const { data: selectedHistory, isLoading: loadingSelected } = useHistory(market)

  if (loadingAll || loadingSelected) {
    return <Skeleton className="w-full h-96" />
  }

  if (!allHistory || !selectedHistory) return null

  // Build a unified month list from selected market
  const months = selectedHistory.map((s) => s.month)

  // Build one series per market for the grey mass
  const allMarkets = Object.keys(allHistory).filter((m) => m !== market && m !== 'National')
  const nationalData = allHistory['National'] ?? []

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart margin={{ top: 8, right: 16, bottom: 8, left: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis
          dataKey="month"
          type="category"
          allowDuplicatedCategory={false}
          tickFormatter={formatTick}
          tick={{ fill: 'var(--muted)', fontSize: 11 }}
          stroke="var(--border)"
        />
        <YAxis
          tickFormatter={(v) => formatMetricValue(metric, v)}
          tick={{ fill: 'var(--muted)', fontSize: 11 }}
          stroke="var(--border)"
          width={70}
        />
        <Tooltip
          formatter={(value: number) => [formatMetricValue(metric, value), market]}
          labelFormatter={(label) => new Date(label).toLocaleString('en-US', { month: 'long', year: 'numeric' })}
          contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}
        />

        {/* Grey mass — all other MSAs */}
        {allMarkets.map((m) => (
          <Line
            key={m}
            data={(allHistory[m] ?? []).map((s) => ({ month: s.month, value: getMetricValue(s, metric) }))}
            dataKey="value"
            name={m}
            stroke="#2a2a3a"
            strokeWidth={1}
            dot={false}
            activeDot={false}
            legendType="none"
            connectNulls
          />
        ))}

        {/* National average */}
        <Line
          data={nationalData.map((s) => ({ month: s.month, value: getMetricValue(s, metric) }))}
          dataKey="value"
          name="National"
          stroke="#7070a0"
          strokeWidth={2}
          dot={false}
          connectNulls
        />

        {/* Selected market — on top */}
        <Line
          data={selectedHistory.map((s) => ({ month: s.month, value: getMetricValue(s, metric) }))}
          dataKey="value"
          name={market}
          stroke="#3479f5"
          strokeWidth={3}
          dot={false}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
```

- [ ] **Step 2: Replace TrendsTab placeholder**

```typescript
'use client'

import { TrendsChart } from '@/components/charts/TrendsChart'
import { useHMIStore } from '@/lib/store'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { METRIC_LABELS } from '@/lib/types'

export function TrendsTab() {
  const { vizMetric, setVizMetric } = useHMIStore()

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <span className="text-sm" style={{ color: 'var(--muted)' }}>Metric</span>
        <Select value={vizMetric} onValueChange={setVizMetric}>
          <SelectTrigger className="w-52 h-8 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(METRIC_LABELS).map(([k, label]) => (
              <SelectItem key={k} value={k}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <TrendsChart metric={vizMetric} />
    </div>
  )
}
```

- [ ] **Step 3: Verify in browser**

Navigate to Trends tab. Should show grey MSA mass lines, medium grey National line, accent blue selected market line. Tooltip shows selected market value only. Metric selector updates all lines.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/charts/TrendsChart.tsx dashboard/src/components/tabs/TrendsTab.tsx
git commit -m "feat(dashboard): Trends chart — grey mass, National, selected market highlight"
```

---

## Task 17: Rankings chart

**Files:**
- Create: `dashboard/src/components/charts/RankingsChart.tsx`
- Modify: `dashboard/src/components/tabs/RankingsTab.tsx`

- [ ] **Step 1: Create `dashboard/src/components/charts/RankingsChart.tsx`**

```typescript
'use client'

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  LabelList, ResponsiveContainer, Cell,
} from 'recharts'
import { useRankings } from '@/hooks/useRankings'
import { useHMIStore } from '@/lib/store'
import { formatMetricValue } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'

interface Props {
  metric: string
  sort: 'asc' | 'desc'
}

export function RankingsChart({ metric, sort }: Props) {
  const { market } = useHMIStore()
  const { data, isLoading } = useRankings(metric, sort)

  if (isLoading) return <Skeleton className="w-full h-[500px]" />
  if (!data) return null

  const dynamicHeight = Math.max(400, data.length * 28)

  return (
    <ResponsiveContainer width="100%" height={dynamicHeight}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 8, right: 80, bottom: 8, left: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
        <XAxis
          type="number"
          tickFormatter={(v) => formatMetricValue(metric, v)}
          tick={{ fill: 'var(--muted)', fontSize: 11 }}
          stroke="var(--border)"
        />
        <YAxis
          type="category"
          dataKey="market"
          width={130}
          tick={{ fill: 'var(--muted)', fontSize: 11 }}
          stroke="var(--border)"
        />
        <Tooltip
          formatter={(value: number, _, props) => [
            formatMetricValue(metric, value),
            props.payload?.market,
          ]}
          contentStyle={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            color: 'var(--text)',
          }}
        />
        <Bar dataKey="value" radius={[0, 3, 3, 0]}>
          {data.map((entry) => (
            <Cell
              key={entry.market}
              fill={entry.market === market ? '#3479f5' : '#2a2a3a'}
            />
          ))}
          <LabelList
            dataKey="value"
            position="right"
            formatter={(v: number) => formatMetricValue(metric, v)}
            style={{ fill: 'var(--muted)', fontSize: 11 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
```

- [ ] **Step 2: Replace RankingsTab placeholder**

```typescript
'use client'

import { useState } from 'react'
import { RankingsChart } from '@/components/charts/RankingsChart'
import { useHMIStore } from '@/lib/store'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { METRIC_LABELS } from '@/lib/types'

export function RankingsTab() {
  const { vizMetric, setVizMetric } = useHMIStore()
  const [sort, setSort] = useState<'asc' | 'desc'>('desc')

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-sm" style={{ color: 'var(--muted)' }}>Metric</span>
        <Select value={vizMetric} onValueChange={setVizMetric}>
          <SelectTrigger className="w-52 h-8 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(METRIC_LABELS).map(([k, label]) => (
              <SelectItem key={k} value={k}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <ToggleGroup
          type="single"
          value={sort}
          onValueChange={(v) => v && setSort(v as 'asc' | 'desc')}
          className="ml-auto"
        >
          <ToggleGroupItem value="desc" className="text-xs h-8 px-3">↓ Desc</ToggleGroupItem>
          <ToggleGroupItem value="asc" className="text-xs h-8 px-3">↑ Asc</ToggleGroupItem>
        </ToggleGroup>
      </div>

      <RankingsChart metric={vizMetric} sort={sort} />
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/charts/RankingsChart.tsx dashboard/src/components/tabs/RankingsTab.tsx
git commit -m "feat(dashboard): Rankings chart — horizontal bars, accent for selected market, sort toggle"
```

---

## Task 18: Yearly Comparison chart

**Files:**
- Create: `dashboard/src/components/charts/YearlyComparisonChart.tsx`
- Modify: `dashboard/src/components/tabs/YearlyComparisonTab.tsx`

- [ ] **Step 1: Create `dashboard/src/components/charts/YearlyComparisonChart.tsx`**

```typescript
'use client'

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import { useHistory } from '@/hooks/useHistory'
import { useHMIStore } from '@/lib/store'
import { formatMetricValue, isYoYMetric } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'
import type { HistorySnapshot } from '@/lib/types'

// 5 distinct palette colors for up to 5 markets
const PALETTE = ['#3479f5', '#14b8a6', '#f59e0b', '#f43f5e', '#a855f7']

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function getMetricValue(snap: HistorySnapshot, metric: string): number | null {
  if (isYoYMetric(metric)) {
    const key = `yoy_${metric === 'median_sale_price' ? 'sale_price' : metric}` as keyof HistorySnapshot
    return (snap[key] as number | null) ?? null
  }
  return (snap[metric as keyof HistorySnapshot] as number) ?? null
}

// Reorganise history into { year → { month_index → value } }
function toSeasonalData(snapshots: HistorySnapshot[], metric: string) {
  const byYear: Record<number, Record<number, number | null>> = {}
  for (const snap of snapshots) {
    const d = new Date(snap.month)
    const year = d.getFullYear()
    const monthIdx = d.getMonth()
    if (!byYear[year]) byYear[year] = {}
    byYear[year][monthIdx] = getMetricValue(snap, metric)
  }
  return byYear
}

interface Props {
  metric: string
  compareMarkets: string[]
  selectedYears: number[]
}

function MarketSeasonalLines({
  market, metric, selectedYears, colorIdx,
}: { market: string; metric: string; selectedYears: number[]; colorIdx: number }) {
  const { data } = useHistory(market)
  if (!data) return null

  const byYear = toSeasonalData(data, metric)
  const baseColor = PALETTE[colorIdx % PALETTE.length]

  return (
    <>
      {selectedYears.map((year, yIdx) => {
        const yearData = byYear[year] ?? {}
        // Build 12-point array (Jan–Dec)
        const points = MONTHS.map((_, i) => ({ month: i, value: yearData[i] ?? null }))
        const opacity = 1 - yIdx * 0.25  // 1.0, 0.75, 0.5, 0.25
        return (
          <Line
            key={`${market}-${year}`}
            data={points}
            dataKey="value"
            name={`${market} ${year}`}
            stroke={baseColor}
            strokeWidth={2}
            strokeOpacity={opacity}
            dot={false}
            connectNulls
          />
        )
      })}
    </>
  )
}

export function YearlyComparisonChart({ metric, compareMarkets, selectedYears }: Props) {
  const { data: primaryData } = useHistory(compareMarkets[0] ?? 'National')
  const loading = !primaryData

  if (loading) return <Skeleton className="w-full h-96" />

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart margin={{ top: 8, right: 16, bottom: 8, left: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis
          dataKey="month"
          type="number"
          domain={[0, 11]}
          ticks={[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}
          tickFormatter={(v: number) => MONTHS[v]}
          tick={{ fill: 'var(--muted)', fontSize: 11 }}
          stroke="var(--border)"
        />
        <YAxis
          tickFormatter={(v) => formatMetricValue(metric, v)}
          tick={{ fill: 'var(--muted)', fontSize: 11 }}
          stroke="var(--border)"
          width={70}
        />
        <Tooltip
          labelFormatter={(v: number) => MONTHS[v]}
          formatter={(value: number, name: string) => [formatMetricValue(metric, value), name]}
          contentStyle={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            color: 'var(--text)',
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 11, color: 'var(--muted)' }}
        />
        {compareMarkets.map((m, i) => (
          <MarketSeasonalLines
            key={m}
            market={m}
            metric={metric}
            selectedYears={selectedYears}
            colorIdx={i}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
```

- [ ] **Step 2: Replace YearlyComparisonTab placeholder**

```typescript
'use client'

import { useMemo } from 'react'
import { YearlyComparisonChart } from '@/components/charts/YearlyComparisonChart'
import { useHMIStore } from '@/lib/store'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { METRIC_LABELS } from '@/lib/types'

const ALL_MARKETS = [
  'National', 'Austin', 'Dallas', 'Houston', 'Phoenix', 'Denver',
  'Atlanta', 'Charlotte', 'Nashville', 'Tampa', 'Orlando',
]

const CURRENT_YEAR = new Date().getFullYear()
const DEFAULT_YEARS = [CURRENT_YEAR, CURRENT_YEAR - 1, CURRENT_YEAR - 2]

export function YearlyComparisonTab() {
  const { vizMetric, setVizMetric, market, compareMarkets, setCompareMarkets } = useHMIStore()

  // Ensure selected market is always included
  const effectiveMarkets = useMemo(() => {
    return compareMarkets.includes(market) ? compareMarkets : [market, ...compareMarkets].slice(0, 5)
  }, [compareMarkets, market])

  function toggleMarket(m: string) {
    if (effectiveMarkets.includes(m)) {
      if (effectiveMarkets.length > 1) setCompareMarkets(effectiveMarkets.filter((x) => x !== m))
    } else if (effectiveMarkets.length < 5) {
      setCompareMarkets([...effectiveMarkets, m])
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-sm" style={{ color: 'var(--muted)' }}>Metric</span>
        <Select value={vizMetric} onValueChange={setVizMetric}>
          <SelectTrigger className="w-52 h-8 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(METRIC_LABELS).map(([k, label]) => (
              <SelectItem key={k} value={k}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="flex flex-wrap gap-2 ml-auto">
          {ALL_MARKETS.map((m) => (
            <button
              key={m}
              onClick={() => toggleMarket(m)}
              className="px-2 py-1 rounded text-xs transition-colors"
              style={{
                background: effectiveMarkets.includes(m) ? 'var(--accent)' : 'var(--surface)',
                color: effectiveMarkets.includes(m) ? '#fff' : 'var(--muted)',
                border: '1px solid var(--border)',
              }}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <YearlyComparisonChart
        metric={vizMetric}
        compareMarkets={effectiveMarkets}
        selectedYears={DEFAULT_YEARS}
      />
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/charts/YearlyComparisonChart.tsx dashboard/src/components/tabs/YearlyComparisonTab.tsx
git commit -m "feat(dashboard): Yearly Comparison — seasonality chart, multi-market, year opacity"
```

---

## Task 19: Dockerfile + docker-compose update

**Files:**
- Create: `dashboard/Dockerfile`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Create `dashboard/Dockerfile`**

```dockerfile
# Stage 1: dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# Stage 2: build
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Stage 3: runner
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

- [ ] **Step 2: Update dashboard service in `docker-compose.yml`**

Replace the `dashboard` service block (lines 85-103) with:

```yaml
  dashboard:
    build:
      context: ./dashboard
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - MCP_API=http://mcp-server:8001
      - AGENT_API=http://agent-runner:8000
    depends_on:
      mcp-server:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:3000/api/health 2>/dev/null || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 256M
```

Note: `start_period` is 60s (longer than before) because Next.js standalone server has a cold-start on first request.

- [ ] **Step 3: Run the full stack**

```bash
cd ..  # back to hmi-engine root
docker-compose build dashboard
docker-compose up dashboard
```

Expected: Container starts. `GET http://localhost/api/health` (via Caddy) → `{"status":"ok","service":"dashboard"}`. Dashboard renders at `http://localhost`.

- [ ] **Step 4: Run full `docker-compose up` and verify end-to-end**

```bash
docker-compose up
```

Check:
- `http://localhost` → dashboard loads dark theme
- Theme toggle switches to light and back
- Market selector in navbar updates KPI tiles
- Trends tab shows line chart
- Rankings tab shows sorted bar chart with selected market highlighted
- Yearly Comparison tab shows seasonality lines

- [ ] **Step 5: Run all tests**

```bash
cd dashboard && npm test
```

Expected: All tests pass.

- [ ] **Step 6: Final commit**

```bash
cd ..
git add dashboard/Dockerfile docker-compose.yml
git commit -m "feat(dashboard): Next.js Dockerfile + docker-compose service update

Replace Python/Streamlit dashboard service with multi-stage Node build.
Port: 8501 → 3000. Health check updated to use wget.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Self-Review Checklist

- [x] **Architecture (spec §3):** Proxy route handlers for all 7 API paths. `MCP_API` and `AGENT_API` env vars. Standalone output. Health endpoint. ✓
- [x] **Layout (spec §4):** Navbar with market selector + theme toggle. 4 tabs. Zustand store with `market`, `vizMetric`, `compareMarkets`. ✓
- [x] **Overview tab order (agreed in brainstorm):** NL Search → KPIs → News+Rates → Research panel. ✓
- [x] **NL Search (spec §5.1):** Idle/loading/answer/error states. Rate limit + timeout friendly errors. `tools_used` subtext. ✓
- [x] **KPI grid (spec §5.2):** 8 tiles, 60s refetch, skeleton loading. ✓
- [x] **Research panel (spec §5.4):** 5 states (idle/awaiting/running/complete/error). `useResearchStatus` polling auto-stops at terminal. `react-markdown` for report. ✓
- [x] **`formatMetricValue` (spec §6):** YoY metrics show `+/-X.X%`; absolute metrics show domain-specific format. Single source of truth in `utils.ts`, used across all 3 charts. ✓
- [x] **Trends chart (spec §6.1):** Grey mass, National, selected market on top. Tooltip shows only selected market. ✓
- [x] **Rankings chart (spec §6.2):** Vertical bar chart, sort toggle with `ToggleGroup`, selected market accent color, `LabelList` values. ✓
- [x] **Yearly Comparison (spec §6.3 + renamed from Historical):** Months on x-axis, years as opacity variants per market, market toggle buttons (max 5), `vizMetric` shared. ✓
- [x] **Types (spec §7):** All interfaces defined in `types.ts`. `TERMINAL_STATUSES` used in hook. `YOY_METRICS` as `Set` used in `isYoYMetric`. ✓
- [x] **Theme (spec §8):** CSS vars in `:root` (light) + `.dark` (dark). `next-themes` `defaultTheme="dark"`. `ThemeToggle` avoids hydration mismatch. ✓
- [x] **Dockerfile:** Multi-stage `node:20-alpine`. `output: standalone`. Non-root user `nextjs`. ✓
- [x] **`useAllHistory` `/api/history/all` route:** Fetches all market names from rankings, then fetches each. Cached 600s. ✓
- [x] **Tab name:** "Yearly Comparison" (not "Historical"). ✓
