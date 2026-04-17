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
