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
