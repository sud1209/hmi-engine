'use client'

import { useEffect, useState } from 'react'
import { ThemeToggle } from './ThemeToggle'
import { useHMIStore } from '@/lib/store'
import { BarChart3, MapPin } from 'lucide-react'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

const MARKETS = [
  'National', 'Austin', 'Dallas', 'Houston', 'Phoenix', 'Denver',
  'Atlanta', 'Charlotte', 'Nashville', 'Tampa', 'Orlando',
]

function LiveBadge() {
  return (
    <div className="flex items-center gap-1.5">
      <span className="relative flex h-2 w-2">
        <span
          className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-70"
          style={{ background: '#22c55e' }}
        />
        <span
          className="relative inline-flex h-2 w-2 rounded-full"
          style={{ background: '#22c55e' }}
        />
      </span>
      <span className="text-xs font-medium" style={{ color: '#22c55e' }}>Live</span>
    </div>
  )
}

function NavDivider() {
  return (
    <div className="h-4 w-px" style={{ background: 'var(--border-color)' }} />
  )
}

function CurrentDate() {
  const [label, setLabel] = useState('')
  useEffect(() => {
    setLabel(new Date().toLocaleDateString('en-US', {
      weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
    }))
  }, [])
  if (!label) return <div className="w-28 h-4" />
  return (
    <span className="text-xs tabular-nums" style={{ color: 'var(--muted)' }}>{label}</span>
  )
}

export function Navbar() {
  const { market, setMarket } = useHMIStore()

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 h-16"
      style={{
        background: 'color-mix(in srgb, var(--surface) 90%, transparent)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: '1px solid var(--border-color)',
        boxShadow: '0 1px 12px rgba(0,0,0,0.12)',
      }}
    >
      {/* ── Brand ── */}
      <div className="flex items-center gap-3">
        <div
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
          style={{
            background: 'var(--accent)',
            boxShadow: '0 0 12px rgba(52,121,245,0.4)',
          }}
        >
          <BarChart3 size={17} color="#fff" strokeWidth={2.2} />
        </div>

        <div className="flex flex-col justify-center leading-none gap-1">
          <span className="text-sm font-bold tracking-tight" style={{ color: 'var(--text)' }}>
            <span style={{ color: 'var(--accent)' }}>HMI</span>
            {' '}Engine
          </span>
          <span className="text-[10px] font-medium tracking-wide uppercase" style={{ color: 'var(--muted)' }}>
            US Housing Market Intelligence
          </span>
        </div>
      </div>

      {/* ── Market selector ── */}
      <div
        className="flex items-center gap-2 rounded-lg px-3 py-1.5"
        style={{
          border: '1px solid var(--border-color)',
          background: 'var(--bg)',
        }}
      >
        <MapPin size={13} style={{ color: 'var(--accent)', flexShrink: 0 }} />
        <span className="text-xs font-medium" style={{ color: 'var(--muted)' }}>Market</span>
        <div className="h-3.5 w-px mx-0.5" style={{ background: 'var(--border-color)' }} />
        <Select value={market} onValueChange={setMarket}>
          <SelectTrigger
            className="h-auto border-0 shadow-none p-0 text-sm font-semibold focus:ring-0 w-[110px] bg-transparent"
            style={{ color: 'var(--text)' }}
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {MARKETS.map((m) => (
              <SelectItem key={m} value={m}>{m}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* ── Right controls ── */}
      <div className="flex items-center gap-3">
        <LiveBadge />
        <NavDivider />
        <CurrentDate />
        <NavDivider />
        <ThemeToggle />
      </div>
    </nav>
  )
}
