'use client'

import { useTheme } from 'next-themes'
import { Sun, Moon } from 'lucide-react'
import { useEffect, useState } from 'react'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  // Avoid hydration mismatch
  useEffect(() => setMounted(true), [])
  if (!mounted) return <div className="w-9 h-9" />

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors"
      style={{ border: '1px solid var(--border-color)', background: 'var(--bg)' }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg)')}
      aria-label="Toggle theme"
    >
      {theme === 'dark'
        ? <Sun size={15} style={{ color: 'var(--muted)' }} />
        : <Moon size={15} style={{ color: 'var(--muted)' }} />
      }
    </button>
  )
}
