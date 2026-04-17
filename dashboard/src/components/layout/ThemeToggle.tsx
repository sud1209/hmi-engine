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
      className="p-2 rounded-md hover:bg-[var(--surface)] transition-colors"
      aria-label="Toggle theme"
    >
      {theme === 'dark'
        ? <Sun size={18} style={{ color: 'var(--muted)' }} />
        : <Moon size={18} style={{ color: 'var(--muted)' }} />
      }
    </button>
  )
}
