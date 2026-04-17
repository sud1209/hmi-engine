'use client'

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import { useHistory } from '@/hooks/useHistory'
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
          tickFormatter={(v) => formatMetricValue(metric, v)}
          tick={{ fill: 'var(--muted)', fontSize: 11 }}
          stroke="var(--border-color)"
          width={70}
        />
        <Tooltip
          labelFormatter={(v: number) => MONTHS[v]}
          formatter={(value: number, name: string) => [formatMetricValue(metric, value), name]}
          contentStyle={{
            background: 'var(--surface)',
            border: '1px solid var(--border-color)',
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
