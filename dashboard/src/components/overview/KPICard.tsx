import { Skeleton } from '@/components/ui/skeleton'

interface KPICardProps {
  label: string
  value: string
  loading?: boolean
}

export function KPICard({ label, value, loading }: KPICardProps) {
  return (
    <div
      className="rounded-lg p-4 flex flex-col gap-2"
      style={{ background: 'var(--surface)', border: '1px solid var(--border-color)' }}
    >
      <span
        className="text-xs font-medium uppercase tracking-widest"
        style={{ color: 'var(--muted)' }}
      >
        {label}
      </span>
      {loading
        ? <Skeleton className="h-8 w-3/4" />
        : <span className="text-2xl font-bold" style={{ color: 'var(--text)' }}>{value}</span>
      }
    </div>
  )
}
