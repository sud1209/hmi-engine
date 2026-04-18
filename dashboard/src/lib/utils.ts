import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { YOY_METRICS } from './types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function isYoYMetric(metric: string): boolean {
  return YOY_METRICS.has(metric)
}

export function formatMetricValue(metric: string, value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'

  if (isYoYMetric(metric)) {
    const sign = value >= 0 ? '+' : ''
    return `${sign}${value.toFixed(1)}%`
  }

  return formatAbsoluteValue(metric, value)
}

// Format a metric as its raw absolute value — used where YoY % is not appropriate
// (e.g. Yearly Comparison chart which plots actual values, not year-over-year change)
export function formatAbsoluteValue(metric: string, value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'

  switch (metric) {
    case 'median_sale_price':
      return `$${(value / 1000).toFixed(0)}K`
    case 'active_listings':
    case 'sales_volume':
    case 'new_listings':
      if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
      if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`
      return String(Math.round(value))
    case 'median_dom':
      return `${Math.round(value)} days`
    case 'months_supply':
      return `${value.toFixed(1)} mo`
    case 'price_per_sqft':
      return `$${Math.round(value)}`
    case 'mortgage_rate_30yr':
      return `${value.toFixed(2)}%`
    default:
      return String(value)
  }
}
