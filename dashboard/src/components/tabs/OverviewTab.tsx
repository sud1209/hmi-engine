import { NLSearchBar } from '@/components/overview/NLSearchBar'
import { KPIGrid } from '@/components/overview/KPIGrid'
import { NewsPanel } from '@/components/overview/NewsPanel'
import { MortgageRatesTable } from '@/components/overview/MortgageRatesTable'
import { ResearchPanel } from '@/components/overview/ResearchPanel'

export function OverviewTab() {
  return (
    <div className="space-y-8">
      {/* 1. NL Search — hero position */}
      <NLSearchBar />

      {/* 2. KPI tiles */}
      <KPIGrid />

      {/* 3. News + Rates two-column */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3"><NewsPanel /></div>
        <div className="lg:col-span-2"><MortgageRatesTable /></div>
      </div>

      {/* 4. Research panel (collapsible) */}
      <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
        <ResearchPanel />
      </div>
    </div>
  )
}
