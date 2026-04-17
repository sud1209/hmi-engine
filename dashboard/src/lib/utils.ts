import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { YOY_METRICS } from './types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function isYoYMetric(metric: string): boolean {
  return YOY_METRICS.has(metric)
}

export function formatMetricValue(metric: string, value: number): string {
  if (value === null || value === undefined) return '—'

  if (isYoYMetric(metric)) {
    const sign = value >= 0 ? '+' : ''
    return `${sign}${value.toFixed(1)}%`
  }

  switch (metric) {
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
