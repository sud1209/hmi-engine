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
