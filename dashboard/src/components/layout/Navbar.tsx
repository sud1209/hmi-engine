'use client'

import { ThemeToggle } from './ThemeToggle'
import { useHMIStore } from '@/lib/store'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

const MARKETS = [
  'National', 'Austin', 'Dallas', 'Houston', 'Phoenix', 'Denver',
  'Atlanta', 'Charlotte', 'Nashville', 'Tampa', 'Orlando',
]

export function Navbar() {
  const { market, setMarket } = useHMIStore()

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 h-14 border-b"
      style={{ background: 'var(--surface)', borderColor: 'var(--border-color)' }}
    >
      <span className="font-semibold text-sm tracking-tight" style={{ color: 'var(--text)' }}>
        HMI Engine
      </span>

      <Select value={market} onValueChange={setMarket}>
        <SelectTrigger className="w-44 h-8 text-sm">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {MARKETS.map((m) => (
            <SelectItem key={m} value={m}>{m}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <ThemeToggle />
    </nav>
  )
}
