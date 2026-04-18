'use client'

import { Navbar } from '@/components/layout/Navbar'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { OverviewTab } from '@/components/tabs/OverviewTab'
import { TrendsTab } from '@/components/tabs/TrendsTab'
import { RankingsTab } from '@/components/tabs/RankingsTab'
import { YearlyComparisonTab } from '@/components/tabs/YearlyComparisonTab'

export default function Page() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Navbar />
      <main className="pt-16 px-6 pb-8 max-w-screen-xl mx-auto">
        <Tabs defaultValue="overview" className="mt-6">
          <TabsList className="folder-tab-list">
            <TabsTrigger value="overview" className="folder-tab-trigger">Overview</TabsTrigger>
            <TabsTrigger value="trends" className="folder-tab-trigger">Trends</TabsTrigger>
            <TabsTrigger value="rankings" className="folder-tab-trigger">Rankings</TabsTrigger>
            <TabsTrigger value="yearly" className="folder-tab-trigger">Yearly Comparison</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="folder-tab-content"><OverviewTab /></TabsContent>
          <TabsContent value="trends" className="folder-tab-content"><TrendsTab /></TabsContent>
          <TabsContent value="rankings" className="folder-tab-content"><RankingsTab /></TabsContent>
          <TabsContent value="yearly" className="folder-tab-content"><YearlyComparisonTab /></TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
