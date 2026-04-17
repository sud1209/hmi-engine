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
                border: '1px solid var(--border-color)',
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
