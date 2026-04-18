'use client'

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  LabelList, ResponsiveContainer, Cell,
} from 'recharts'
import { useRankings } from '@/hooks/useRankings'
import { useHMIStore } from '@/lib/store'
import { formatMetricValue, isYoYMetric } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'

interface Props {
  metric: string
  sort: 'asc' | 'desc'
}

export function RankingsChart({ metric, sort }: Props) {
  const { market } = useHMIStore()
  const { data, isLoading } = useRankings(metric, sort)
  const useYoY = isYoYMetric(metric)

  if (isLoading) return <Skeleton className="w-full h-[500px]" />
  if (!data) return null

  // For YoY metrics use yoy_change; for absolute metrics use value
  const chartData = data.map((row) => ({
    ...row,
    displayValue: useYoY ? (row.yoy_change ?? 0) : row.value,
  }))

  const dynamicHeight = Math.max(400, chartData.length * 28)

  return (
    <ResponsiveContainer width="100%" height={dynamicHeight}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 8, right: 80, bottom: 8, left: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" horizontal={false} />
        <XAxis
          type="number"
          tickFormatter={(v) => formatMetricValue(metric, v)}
          tick={{ fill: 'var(--muted)', fontSize: 11 }}
          stroke="var(--border-color)"
        />
        <YAxis
          type="category"
          dataKey="market"
          width={130}
          tick={{ fill: 'var(--muted)', fontSize: 11 }}
          stroke="var(--border-color)"
        />
        <Tooltip
          formatter={(value: number, _, props) => [
            formatMetricValue(metric, value),
            props.payload?.market,
          ]}
          contentStyle={{
            background: 'var(--surface)',
            border: '1px solid var(--border-color)',
            color: 'var(--text)',
          }}
        />
        <Bar dataKey="displayValue" radius={[0, 3, 3, 0]}>
          {chartData.map((entry) => (
            <Cell
              key={entry.market}
              fill={entry.market === market ? '#3479f5' : '#2a2a3a'}
            />
          ))}
          <LabelList
            dataKey="displayValue"
            position="right"
            formatter={(v: number) => formatMetricValue(metric, v)}
            style={{ fill: 'var(--muted)', fontSize: 11 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
