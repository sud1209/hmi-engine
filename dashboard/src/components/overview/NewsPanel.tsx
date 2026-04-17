'use client'

import { useDashboard } from '@/hooks/useDashboard'
import { useHMIStore } from '@/lib/store'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import type { NewsItem } from '@/lib/types'

const RELEVANCE_COLORS: Record<string, string> = {
  high: '#22c55e',
  medium: '#f59e0b',
  low: '#6b7280',
}

function NewsCard({ item }: { item: NewsItem }) {
  return (
    <div
      className="rounded-lg p-4 space-y-2"
      style={{ background: 'var(--surface)', border: '1px solid var(--border-color)' }}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium leading-snug" style={{ color: 'var(--text)' }}>
          {item.headline}
        </p>
        <span
          className="mt-1 flex-shrink-0 w-2 h-2 rounded-full"
          style={{ background: RELEVANCE_COLORS[item.relevance_score] ?? '#6b7280' }}
        />
      </div>
      {item.summary && (
        <p className="text-xs leading-relaxed" style={{ color: 'var(--muted)' }}>
          {item.summary}
        </p>
      )}
      <Badge variant="outline" className="text-xs">{item.source}</Badge>
    </div>
  )
}

export function NewsPanel() {
  const { market } = useHMIStore()
  const { data, isLoading } = useDashboard(market)
  const news = data?.recent_news ?? []

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
        Market News
      </h3>
      {isLoading
        ? Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))
        : news.map((item, i) => <NewsCard key={i} item={item} />)
      }
    </div>
  )
}
