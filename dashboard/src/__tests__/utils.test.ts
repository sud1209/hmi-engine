import { formatMetricValue, isYoYMetric, cn } from '@/lib/utils'

describe('isYoYMetric', () => {
  it('returns true for YoY metrics', () => {
    expect(isYoYMetric('active_listings')).toBe(true)
    expect(isYoYMetric('median_sale_price')).toBe(true)
    expect(isYoYMetric('sales_volume')).toBe(true)
    expect(isYoYMetric('new_listings')).toBe(true)
  })

  it('returns false for absolute metrics', () => {
    expect(isYoYMetric('median_dom')).toBe(false)
    expect(isYoYMetric('months_supply')).toBe(false)
    expect(isYoYMetric('price_per_sqft')).toBe(false)
    expect(isYoYMetric('mortgage_rate_30yr')).toBe(false)
  })
})

describe('formatMetricValue', () => {
  it('formats YoY metrics as percentage with sign', () => {
    expect(formatMetricValue('active_listings', 12.4)).toBe('+12.4%')
    expect(formatMetricValue('active_listings', -5.2)).toBe('-5.2%')
    expect(formatMetricValue('median_sale_price', 0)).toBe('+0.0%')
  })

  it('formats median_dom as days', () => {
    expect(formatMetricValue('median_dom', 28)).toBe('28 days')
  })

  it('formats months_supply with one decimal', () => {
    expect(formatMetricValue('months_supply', 2.4)).toBe('2.4 mo')
  })

  it('formats price_per_sqft as dollars', () => {
    expect(formatMetricValue('price_per_sqft', 248)).toBe('$248')
  })

  it('formats mortgage_rate_30yr as percent', () => {
    expect(formatMetricValue('mortgage_rate_30yr', 6.82)).toBe('6.82%')
  })

  it('returns "—" for null/undefined', () => {
    expect(formatMetricValue('active_listings', null)).toBe('—')
    expect(formatMetricValue('median_dom', undefined)).toBe('—')
  })
})

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('a', 'b')).toBe('a b')
    expect(cn('px-2', 'px-4')).toBe('px-4') // tailwind-merge deduplication
  })
})
