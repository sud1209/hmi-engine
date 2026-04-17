import { create } from 'zustand'

interface HMIStore {
  market: string
  vizMetric: string
  compareMarkets: string[]
  setMarket: (market: string) => void
  setVizMetric: (metric: string) => void
  setCompareMarkets: (markets: string[]) => void
}

export const useHMIStore = create<HMIStore>((set) => ({
  market: 'National',
  vizMetric: 'median_sale_price',
  compareMarkets: ['National'],
  setMarket: (market) => set({ market }),
  setVizMetric: (vizMetric) => set({ vizMetric }),
  setCompareMarkets: (compareMarkets) => set({ compareMarkets }),
}))
