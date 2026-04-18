'use client'

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import { useHistory } from '@/hooks/useHistory'
import { formatAbsoluteValue } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'
import type { HistorySnapshot } from '@/lib/types'

// 5 distinct palette colors for up to 5 markets
const PALETTE = ['#3479f5', '#14b8a6', '#f59e0b', '#f43f5e', '#a855f7']

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// Yearly Comparison always uses raw (absolute) values for direct year-over-year visual comparison
function getMetricValue(snap: HistorySnapshot, metric: string): number | null {
  return (snap[metric as keyof HistorySnapshot] as number) ?? null
}

// Build Jan-Dec points for a given market+year from history snapshots
function buildSeasonalPoints(
  snapshots: HistorySnapshot[],
  metric: string,
  year: number,
): { month: number; value: number | null }[] {
  const byMonth: Record<number, number | null> = {}
  for (const snap of snapshots) {
    const d = new Date(snap.month)
    if (d.getFullYear() === year) {
      byMonth[d.getMonth()] = getMetricValue(snap, metric)
    }
  }
  return MONTHS.map((_, i) => ({ month: i, value: byMonth[i] ?? null }))
}

interface MarketYearData {
  market: string
  year: number
  color: string
  opacity: number
  points: { month: number; value: number | null }[]
}

interface Props {
  metric: string
  compareMarkets: string[]
  selectedYears: number[]
}

// Single market loader — fetches history and returns pre-built series
function useMarketSeries(
  markets: string[],
  metric: string,
  selectedYears: number[],
): { series: MarketYearData[]; loading: boolean } {
  const h0 = useHistory(markets[0] ?? 'National')
  const h1 = useHistory(markets[1] ?? '')
  const h2 = useHistory(markets[2] ?? '')
  const h3 = useHistory(markets[3] ?? '')
  const h4 = useHistory(markets[4] ?? '')

  const historyByMarket: Record<string, HistorySnapshot[] | undefined> = {}
  ;[h0, h1, h2, h3, h4].forEach((q, i) => {
    if (markets[i]) historyByMarket[markets[i]] = q.data
  })

  const loading = markets.some((m, i) => {
    const q = [h0, h1, h2, h3, h4][i]
    return q?.isLoading
  })

  const series: MarketYearData[] = []
  markets.forEach((market, colorIdx) => {
    const snapshots = historyByMarket[market]
    if (!snapshots) return
    selectedYears.forEach((year, yIdx) => {
      series.push({
        market,
        year,
        color: PALETTE[colorIdx % PALETTE.length],
        opacity: Math.max(0.2, 1 - yIdx * 0.25),
        points: buildSeasonalPoints(snapshots, metric, year),
      })
    })
  })

  return { series, loading }
}

export function YearlyComparisonChart({ metric, compareMarkets, selectedYears }: Props) {
  const { series, loading } = useMarketSeries(compareMarkets, metric, selectedYears)

  if (loading) return <Skeleton className="w-full h-96" />

  // Merge all series into a single dataset keyed by month index (0-11)
  // Each row: { month: 0..11, [market-year]: value, ... }
  const merged: Record<number, Record<string, number | null>> = {}
  for (let i = 0; i < 12; i++) merged[i] = { month: i }

  for (const s of series) {
    const key = `${s.market} ${s.year}`
    for (const pt of s.points) {
      merged[pt.month][key] = pt.value
    }
  }

  const chartData = Object.values(merged)

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
        <XAxis
          dataKey="month"
          type="number"
          domain={[0, 11]}
          ticks={[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}
          tickFormatter={(v: number) => MONTHS[v]}
          tick={{ fill: 'var(--muted)', fontSize: 11 }}
          stroke="var(--border-color)"
        />
        <YAxis
          tickFormatter={(v) => formatAbsoluteValue(metric, v)}
          tick={{ fill: 'var(--muted)', fontSize: 11 }}
          stroke="var(--border-color)"
          width={70}
        />
        <Tooltip
          labelFormatter={(v: number) => MONTHS[v]}
          formatter={(value: number, name: string) => [formatAbsoluteValue(metric, value), name]}
          contentStyle={{
            background: 'var(--surface)',
            border: '1px solid var(--border-color)',
            color: 'var(--text)',
          }}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: 'var(--muted)' }} />
        {series.map((s) => (
          <Line
            key={`${s.market}-${s.year}`}
            dataKey={`${s.market} ${s.year}`}
            name={`${s.market} ${s.year}`}
            stroke={s.color}
            strokeWidth={2}
            strokeOpacity={s.opacity}
            dot={false}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
