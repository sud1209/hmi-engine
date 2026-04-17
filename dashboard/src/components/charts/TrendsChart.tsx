'use client'

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
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

// Format month string "2023-04-01" → "Apr 23" for January ticks, "Apr" otherwise
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

  // Build one series per non-selected, non-National market for the grey mass
  const allMarkets = Object.keys(allHistory).filter((m) => m !== market && m !== 'National')
  const nationalData = allHistory['National'] ?? []

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart margin={{ top: 8, right: 16, bottom: 8, left: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
        <XAxis
          dataKey="month"
          type="category"
          allowDuplicatedCategory={false}
          tickFormatter={formatTick}
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
          formatter={(value: number) => [formatMetricValue(metric, value), market]}
          labelFormatter={(label) => new Date(label).toLocaleString('en-US', { month: 'long', year: 'numeric' })}
          contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border-color)', color: 'var(--text)' }}
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
