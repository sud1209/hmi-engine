'use client'

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { TooltipProps } from 'recharts'
import { useAllHistory } from '@/hooks/useAllHistory'
import { useHistory } from '@/hooks/useHistory'
import { useHMIStore } from '@/lib/store'
import { formatMetricValue, isYoYMetric } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'
import { METRIC_LABELS, type HistorySnapshot } from '@/lib/types'

// Extract the right value from a snapshot for the current metric
function getMetricValue(snap: HistorySnapshot, metric: string): number | null {
  if (isYoYMetric(metric)) {
    const yoyKey = `yoy_${metric}` as keyof HistorySnapshot
    return (snap[yoyKey] as number | null) ?? null
  }
  return (snap[metric as keyof HistorySnapshot] as number) ?? null
}

// Format month string "2023-04-01" → "Apr 23" for January, "Apr" otherwise
function formatTick(monthStr: string): string {
  const d = new Date(monthStr)
  const month = d.toLocaleString('en-US', { month: 'short' })
  return d.getMonth() === 0 ? `${month} ${String(d.getFullYear()).slice(2)}` : month
}

// Custom tooltip — shows only selected market + National, selected market first
interface CustomTooltipProps extends TooltipProps<number, string> {
  metric: string
  selectedMarket: string
}

function CustomTooltip({ active, payload, label, metric, selectedMarket }: CustomTooltipProps) {
  if (!active || !payload?.length) return null

  const month = new Date(label as string).toLocaleString('en-US', { month: 'long', year: 'numeric' })
  const metricLabel = METRIC_LABELS[metric] ?? metric

  // Selected market first, National second, rest sorted by absolute value descending
  const pinned = payload
    .filter((p) => p.name === selectedMarket || p.name === 'National')
    .sort((a) => (a.name === selectedMarket ? -1 : 1))
  const others = payload
    .filter((p) => p.name !== selectedMarket && p.name !== 'National')
    .sort((a, b) => Math.abs((b.value as number) ?? 0) - Math.abs((a.value as number) ?? 0))
  const entries = [...pinned, ...others]

  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border-color)',
      borderRadius: 6,
      padding: '8px 12px',
      minWidth: 200,
      maxHeight: 320,
      overflowY: 'auto',
    }}>
      <p style={{ fontSize: 11, fontWeight: 600, marginBottom: 6, color: 'var(--text)', opacity: 0.7 }}>
        {month} · {metricLabel}
      </p>
      {pinned.map((p) => (
        <div
          key={p.name}
          style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3, fontSize: 12 }}
        >
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: p.color ?? '#888',
            flexShrink: 0,
          }} />
          <span style={{ color: 'var(--text)', flex: 1, fontWeight: p.name === selectedMarket ? 600 : 400 }}>
            {p.name}
          </span>
          <span style={{ color: 'var(--text)', fontWeight: 600, marginLeft: 16 }}>
            {formatMetricValue(metric, p.value as number)}
          </span>
        </div>
      ))}
      {others.length > 0 && (
        <>
          <div style={{ borderTop: '1px solid var(--border-color)', margin: '5px 0' }} />
          {others.map((p) => (
            <div
              key={p.name}
              style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3, fontSize: 11 }}
            >
              <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: 'var(--muted)',
                flexShrink: 0,
              }} />
              <span style={{ color: 'var(--text)', flex: 1, opacity: 0.75 }}>
                {p.name}
              </span>
              <span style={{ color: 'var(--text)', marginLeft: 16, opacity: 0.75 }}>
                {formatMetricValue(metric, p.value as number)}
              </span>
            </div>
          ))}
        </>
      )}
    </div>
  )
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
        <Tooltip content={<CustomTooltip metric={metric} selectedMarket={market} />} />

        {/* Grey mass — all other MSAs, included in tooltip payload but styled smaller */}
        {allMarkets.map((m) => (
          <Line
            key={m}
            data={(allHistory[m] ?? []).map((s) => ({ month: s.month, value: getMetricValue(s, metric) }))}
            dataKey="value"
            name={m}
            stroke="#2a2a3a"
            strokeWidth={1}
            dot={false}
            activeDot={{ r: 2, fill: '#2a2a3a' }}
            legendType="none"
            connectNulls
          />
        ))}

        {/* National average */}
        <Line
          data={nationalData.map((s) => ({ month: s.month, value: getMetricValue(s, metric) }))}
          dataKey="value"
          name="National"
          stroke="#6a90c8"
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
