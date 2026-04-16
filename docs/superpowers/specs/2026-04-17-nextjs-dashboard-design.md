---
title: HMI Engine — Next.js Dashboard Redesign
date: 2026-04-17
status: agreed
authors: [engineering]
---

# HMI Engine — Next.js Dashboard Redesign

## Table of Contents

1. [Context](#1-context)
2. [Goals](#2-goals)
3. [Architecture](#3-architecture)
4. [Layout & Navigation](#4-layout--navigation)
5. [Overview Tab](#5-overview-tab)
6. [Visualization Tabs](#6-visualization-tabs)
7. [Data Layer](#7-data-layer)
8. [Theme System](#8-theme-system)
9. [File Structure](#9-file-structure)
10. [What Is Not Changing](#10-what-is-not-changing)

---

## 1. Context

The current dashboard is a Streamlit application (`dashboard/dashboard.py`, ~350 lines). Streamlit imposes a full-page rerun model, limited styling control, and a visual ceiling that undersells the product. This spec replaces it with a Next.js 15 + Tailwind CSS + shadcn/ui application that slots into the existing `docker-compose.yml` as a drop-in service replacement. All backend APIs remain unchanged.

---

## 2. Goals

| Goal | Description |
|---|---|
| Drop-in replacement | Same `dashboard` service slot in docker-compose; Caddy routing unchanged |
| Feature parity | All current Streamlit features reproduced with no regressions |
| Visual quality | Polished, differentiated look — not a generic template dashboard |
| Dark default | Dark theme by default, toggleable to light |
| No backend changes | Next.js proxies to existing mcp-server and agent-runner APIs |

---

## 3. Architecture

### Service replacement

The `dashboard/` directory is replaced with a Next.js 15 App Router project. The Dockerfile changes from `python:3.12-slim` (Streamlit) to a multi-stage Node build:

```dockerfile
# Stage 1: builder
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: runner
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

`next.config.ts` sets `output: 'standalone'` for the minimal production image.

### API proxy

The browser never calls mcp-server or agent-runner directly. All client fetches hit Next.js route handlers, which forward to the internal Docker hostnames.

```
Browser → GET /api/dashboard?market=Austin
  → Next.js route handler (src/app/api/dashboard/route.ts)
  → GET http://mcp-server:8001/dashboard?market=Austin
  → response forwarded back to browser
```

Route handlers defined for:

| Next.js route | Proxies to |
|---|---|
| `GET /api/dashboard` | `http://mcp-server:8001/dashboard` |
| `GET /api/history/[market]` | `http://mcp-server:8001/history/{market}` |
| `GET /api/msa/rankings` | `http://mcp-server:8001/msa/rankings` |
| `POST /api/query` | `http://mcp-server:8001/query` |
| `POST /api/research` | `http://agent-runner:8000/research` |
| `GET /api/research/[runId]/status` | `http://agent-runner:8000/research/{runId}/status` |
| `POST /api/research/[runId]/approve` | `http://agent-runner:8000/research/{runId}/approve` |

Environment variables (server-side only, not exposed to browser):
- `MCP_API=http://mcp-server:8001`
- `AGENT_API=http://agent-runner:8000`

### docker-compose.yml change

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
    test: ["CMD-SHELL", "wget -qO- http://localhost:3000/api/health || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  deploy:
    resources:
      limits:
        cpus: "0.5"
        memory: 256M
```

Port changes from `8501` to `3000`.

---

## 4. Layout & Navigation

### App shell

Fixed top navbar, content below. No sidebar.

**Navbar (fixed, full width):**
- Left: HMI Engine wordmark
- Center: global market `<Select>` — drives all tabs
- Right: dark/light theme toggle (`<Sun>` / `<Moon>` icon from lucide-react)

**Tab bar (sticky, below navbar):**
```
[ Overview ]  [ Trends ]  [ Rankings ]  [ Yearly Comparison ]
```

shadcn/ui `<Tabs>` with pill-style active indicator. Tab content fills the remaining viewport height.

### Global state (Zustand, `src/lib/store.ts`)

```typescript
interface HMIStore {
  market: string               // default: "National"
  vizMetric: string            // default: "median_sale_price"
  compareMarkets: string[]     // default: ["National"]
  setMarket: (m: string) => void
  setVizMetric: (m: string) => void
  setCompareMarkets: (ms: string[]) => void
}
```

Changing `market` in the navbar selector writes to the store. All hooks read from the store — no prop drilling.

---

## 5. Overview Tab

Sections rendered top to bottom:

### 5.1 NL Search bar (hero position)

Full-width `<Input>` with search icon, placeholder `"Ask about the housing market..."`. Submit on Enter or button click.

States:
- **Idle** — just the input
- **Loading** — input disabled, skeleton line below
- **Answer** — answer text in `<p>` with muted `tools_used` below: `"Used: search_houses, get_housing_market_snapshot"`
- **Error** — dismissible `<Alert variant="warning">` with friendly message, no stack trace

Calls `POST /api/query`. Rate limit errors (429) show: `"Too many searches — wait a moment before trying again."` Timeout errors (408) show: `"Search timed out. Try a more specific question."`

### 5.2 KPI tiles

8 tiles, `grid grid-cols-2 sm:grid-cols-4 gap-4`. Each tile is a shadcn `<Card>`:
- Top: metric name in `text-muted-foreground text-xs uppercase tracking-wide`
- Center: value in `text-2xl font-bold`
- Bottom: small trend indicator badge (where data supports it)

Data from `useDashboard(market)`, React Query `staleTime: 60_000`, background refetch every 60 seconds. Loading state: 8 skeleton cards. Error state: inline `<ErrorBanner>`.

KPI fields: `avg_list_price`, `active_listings`, `rate_30yr_fixed`, `median_dom`, `price_per_sqft`, `new_listings_30d`, `price_reductions`, `months_supply`.

### 5.3 Two-column row

`grid grid-cols-1 lg:grid-cols-5 gap-4`

**News panel (lg:col-span-3):** 4 news cards. Each card: headline in medium weight, source name as a small badge, relevance dot (green = high, yellow = medium, grey = low). No truncation on headline.

**Mortgage rates (lg:col-span-2):** shadcn `<Table>` with columns: Term, Rate, Type. 30yr row highlighted with accent-colored rate value. Data from the same `useDashboard` response.

### 5.4 Research panel

shadcn `<Collapsible>`, collapsed by default. Header shows "AI Research" label + chevron icon. Expand reveals the full panel.

**Four internal states:**

**Idle:** Query `<Input>` + "Run Research" `<Button variant="default">`. Submits `POST /api/research`.

**Awaiting approval:** Plan displayed as a bulleted `<ul>`. Two buttons: `<Button variant="default">✓ Approve</Button>` and `<Button variant="outline">✗ Reject</Button>`. POSTs to `/api/research/{runId}/approve`.

**Running:** Indeterminate `<Progress>` bar animation. Label: "Pipeline running — this takes ~30 seconds." Polls `GET /api/research/{runId}/status` every 3 seconds via `useResearchStatus` hook. Polling stops when status reaches `complete`, `rejected`, or `error`.

**Complete:** Markdown report rendered via `react-markdown` in a scrollable container (`max-h-96 overflow-y-auto`). KPI grid below (metro-specific: sample size, avg price, estimated ROI). "Run another" button resets to Idle state.

**Error:** `<Alert variant="destructive">` with the error string. "Try again" button resets to Idle.

---

## 6. Visualization Tabs

All three tabs include a shared **metric selector** `<Select>` in their tab header. Changing the metric writes to `store.vizMetric`. Available options and their display mode:

| Metric key | Label | Display |
|---|---|---|
| `active_listings` | Active Listings | YoY % |
| `median_sale_price` | Median Sale Price | YoY % |
| `sales_volume` | Sales Volume | YoY % |
| `new_listings` | New Listings | YoY % |
| `median_dom` | Days on Market | Absolute |
| `months_supply` | Months Supply | Absolute |
| `price_per_sqft` | Price / sqft | Absolute |
| `mortgage_rate_30yr` | Mortgage Rate | Absolute |

`formatMetricValue(metric, value)` — single utility function, returns formatted string. Used for axis ticks, tooltip values, and bar labels everywhere.

### 6.1 Trends tab

Recharts `<LineChart>` inside `<ResponsiveContainer width="100%" height={400}>`.

Data from `useHistory(market)` and a separate `useAllHistory()` that fetches all MSAs. Three series layers rendered in order (back to front):

1. **All non-selected MSAs** — one `<Line>` per MSA, `stroke="#2a2a3a"`, `strokeWidth={1}`, `dot={false}`, `activeDot={false}`. No tooltip contribution.
2. **National average** — `stroke="#7070a0"`, `strokeWidth={2}`, `dot={false}`.
3. **Selected market** — `stroke="#3479f5"`, `strokeWidth={3}`, `dot={false}`. Tooltip shows this line's value only.

X-axis: monthly ticks, `tickFormatter` showing abbreviated month+year for Jan ticks only (e.g., "Jan 23"). Y-axis: `tickFormatter` using `formatMetricValue`.

Tooltip shows: selected market name + formatted value. Does not show all 30 MSA values.

Loading state: full-height skeleton rectangle.

### 6.2 Rankings tab

Recharts `<BarChart layout="vertical">` inside `<ResponsiveContainer width="100%" height={dynamicHeight}>`.

Dynamic height: `Math.max(400, markets.length * 28)` — ensures all bars are visible without scrolling the chart itself.

Sort direction toggle: shadcn `<ToggleGroup type="single">` with "↑ Asc" and "↓ Desc" options, in the tab header row next to the metric selector. Changing sort direction re-fetches `useRankings(metric, sort)`.

Bar styling:
- Selected market: `fill="#3479f5"`
- All others: `fill="#2a2a3a"`
- Hover: all bars show `fill="#3479f5"` on active

Bar order: controlled by `yAxis={{ type: "category", dataKey: "market", width: 120 }}` with `data` array pre-sorted by the API. Recharts renders bars in data order for vertical layout — no client-side re-sort needed.

Value labels: `<LabelList dataKey="value" position="right" formatter={formatMetricValue} />`.

### 6.3 Yearly Comparison tab

Recharts `<LineChart>` showing months (Jan–Dec) on the x-axis, one line per selected year.

**Market selector:** `<MultiSelect>` (custom shadcn-based component, max 5 selections) above the chart. Defaults to `[store.market]`. Each selected market fetches `useHistory(market)` independently. All markets' data rendered on the same chart.

**Year selector:** `<MultiSelect>` defaulting to last 3 years available in the data. One `<Line>` per (market × year) combination.

**Color assignment:** Fixed 5-color palette per market (e.g., accent blue, teal, amber, rose, purple). Each selected market gets one color. Years within that market use opacity variants of the same color: current year = 100%, previous year = 70%, two years ago = 50%. This means 3 markets × 3 years = 9 lines remain visually separable — same-market lines cluster by hue, different-market lines are immediately distinct by color.

**Range slider:** `<Slider>` below the chart to narrow the year range. Implemented as a controlled Recharts `<ReferenceArea>` or a standard HTML range input that filters the data array.

**Current value annotation:** `<ReferenceLine>` at the final data point per line, with a `<Label>` showing the formatted value.

---

## 7. Data Layer

### API client (`src/lib/api.ts`)

Single module, all typed. No raw `fetch` calls outside this file.

```typescript
export const api = {
  getDashboard: (market: string): Promise<DashboardResponse> => ...
  getHistory: (market: string, years?: number): Promise<HistorySnapshot[]> => ...
  getAllHistory: (): Promise<Record<string, HistorySnapshot[]>> => ...
  getRankings: (metric: string, sort: 'asc' | 'desc'): Promise<RankingRow[]> => ...
  nlQuery: (query: string): Promise<NLQueryResponse> => ...
  startResearch: (query: string): Promise<ResearchRun> => ...
  getResearchStatus: (runId: string): Promise<ResearchRun> => ...
  approveResearch: (runId: string, approved: boolean): Promise<ResearchRun> => ...
}
```

All functions throw typed errors. HTTP 4xx/5xx responses throw `ApiError` with `status` and `message` fields.

### React Query hooks (`src/hooks/`)

| File | Hook | Notes |
|---|---|---|
| `useDashboard.ts` | `useDashboard(market)` | `refetchInterval: 60_000` |
| `useHistory.ts` | `useHistory(market, years?)` | `staleTime: 300_000` |
| `useAllHistory.ts` | `useAllHistory()` | `staleTime: 600_000`, fetches all MSAs (heavy — cache for 10 min) |
| `useRankings.ts` | `useRankings(metric, sort)` | `staleTime: 300_000` |
| `useResearchStatus.ts` | `useResearchStatus(runId)` | `refetchInterval: 3_000`, disabled when `runId` is null or status is terminal |

### Types (`src/lib/types.ts`)

Mirrors API response shapes:

```typescript
interface DashboardResponse {
  kpis: Record<string, string>
  recent_news: NewsItem[]
  market_snapshot: MarketSnapshot
  mortgage_rates: MortgageRate[]
}

interface HistorySnapshot {
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

interface RankingRow {
  market: string
  value: number
  rank: number
}

interface ResearchRun {
  run_id: string
  status: 'awaiting_approval' | 'running' | 'complete' | 'rejected' | 'error'
  plan?: string[]
  result?: { report: { report_markdown: string }, dashboard: { kpis: object } }
  error?: string
}

interface NLQueryResponse {
  answer: string
  tools_used: string[]
}
```

---

## 8. Theme System

`next-themes` with `defaultTheme="dark"`, `attribute="class"`. Tailwind `darkMode: "class"`.

CSS variables defined in `src/app/globals.css`:

```css
:root {
  --background: #f8f8fc;
  --surface: #ffffff;
  --border: #e2e2ec;
  --accent: #3479f5;
  --text-primary: #0f0f13;
  --text-muted: #6060a0;
}

.dark {
  --background: #0f0f13;
  --surface: #1a1a24;
  --border: #2a2a3a;
  --accent: #3479f5;
  --text-primary: #e8e8f0;
  --text-muted: #7070a0;
}
```

Mapped to Tailwind tokens in `tailwind.config.ts`:
```typescript
colors: {
  background: 'var(--background)',
  surface: 'var(--surface)',
  border: 'var(--border)',
  accent: 'var(--accent)',
}
```

Theme toggle: `<Button variant="ghost" size="icon">` that calls `setTheme(theme === 'dark' ? 'light' : 'dark')` from `useTheme()`.

---

## 9. File Structure

```
dashboard/
├── Dockerfile
├── package.json
├── next.config.ts              # output: standalone
├── tailwind.config.ts
├── tsconfig.json
├── public/
│   └── favicon.ico
└── src/
    ├── app/
    │   ├── layout.tsx          # ThemeProvider, QueryClientProvider, fonts
    │   ├── page.tsx            # renders <DashboardShell />
    │   ├── globals.css         # CSS variables + base styles
    │   └── api/
    │       ├── dashboard/route.ts
    │       ├── history/[market]/route.ts
    │       ├── msa/
    │       │   └── rankings/route.ts
    │       ├── query/route.ts
    │       └── research/
    │           ├── route.ts
    │           └── [runId]/
    │               ├── status/route.ts
    │               └── approve/route.ts
    ├── components/
    │   ├── ui/                 # shadcn/ui primitives (button, card, tabs, etc.)
    │   ├── layout/
    │   │   ├── Navbar.tsx
    │   │   ├── TabBar.tsx
    │   │   └── ThemeToggle.tsx
    │   ├── overview/
    │   │   ├── NLSearchBar.tsx
    │   │   ├── KPIGrid.tsx
    │   │   ├── KPICard.tsx
    │   │   ├── NewsPanel.tsx
    │   │   ├── MortgageRatesTable.tsx
    │   │   └── ResearchPanel.tsx
    │   └── charts/
    │       ├── TrendsChart.tsx
    │       ├── RankingsChart.tsx
    │       └── YearlyComparisonChart.tsx
    ├── hooks/
    │   ├── useDashboard.ts
    │   ├── useHistory.ts
    │   ├── useAllHistory.ts
    │   ├── useRankings.ts
    │   └── useResearchStatus.ts
    └── lib/
        ├── api.ts              # all fetch calls, typed
        ├── store.ts            # Zustand store
        ├── types.ts            # TypeScript interfaces
        └── utils.ts            # formatMetricValue, cn(), etc.
```

---

## 10. What Is Not Changing

- All mcp-server and agent-runner APIs — unchanged
- docker-compose service names and internal hostnames — unchanged
- Caddy routing rules — unchanged (port differs: 3000 vs 8501, but Caddy proxies by hostname)
- The accent color (#3479f5) — carried over from Streamlit
- All 11 AI capability signals the platform demonstrates — unaffected by this frontend change

---

## Dependencies

| Package | Purpose |
|---|---|
| `next@15` | App Router framework |
| `react@19`, `react-dom@19` | UI runtime |
| `tailwindcss@4` | Utility CSS |
| `shadcn/ui` (CLI) | Component primitives |
| `recharts@2` | Charts |
| `@tanstack/react-query@5` | Data fetching + caching |
| `zustand@5` | Global state |
| `next-themes` | Dark/light toggle |
| `react-markdown` | Render research report |
| `lucide-react` | Icons |

---

*Spec date: 2026-04-17*
