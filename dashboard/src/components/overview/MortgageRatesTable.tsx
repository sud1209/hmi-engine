'use client'

import { useDashboard } from '@/hooks/useDashboard'
import { useHMIStore } from '@/lib/store'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'

export function MortgageRatesTable() {
  const { market } = useHMIStore()
  const { data, isLoading } = useDashboard(market)
  const rates = data?.mortgage_rates ?? []

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
        Mortgage Rates
      </h3>
      <div
        className="rounded-lg overflow-hidden"
        style={{ border: '1px solid var(--border-color)' }}
      >
        {isLoading
          ? <Skeleton className="h-32 w-full" />
          : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Term</TableHead>
                  <TableHead>Rate</TableHead>
                  <TableHead>Type</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rates.map((r) => (
                  <TableRow key={r.term_years}>
                    <TableCell className="text-sm">{r.term_years}yr</TableCell>
                    <TableCell
                      className="text-sm font-semibold"
                      style={r.term_years === 30 ? { color: 'var(--accent)' } : { color: 'var(--text)' }}
                    >
                      {r.rate.toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-xs capitalize" style={{ color: 'var(--muted)' }}>
                      {r.rate_type}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )
        }
      </div>
    </div>
  )
}
