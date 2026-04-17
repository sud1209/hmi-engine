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
      <main className="pt-14 px-6 pb-8 max-w-screen-xl mx-auto">
        <Tabs defaultValue="overview" className="mt-6">
          <TabsList className="mb-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="trends">Trends</TabsTrigger>
            <TabsTrigger value="rankings">Rankings</TabsTrigger>
            <TabsTrigger value="yearly">Yearly Comparison</TabsTrigger>
          </TabsList>

          <TabsContent value="overview"><OverviewTab /></TabsContent>
          <TabsContent value="trends"><TrendsTab /></TabsContent>
          <TabsContent value="rankings"><RankingsTab /></TabsContent>
          <TabsContent value="yearly"><YearlyComparisonTab /></TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
