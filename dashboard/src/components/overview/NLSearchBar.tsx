'use client'

import { useState, FormEvent } from 'react'
import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { api, ApiError } from '@/lib/api'
import { Skeleton } from '@/components/ui/skeleton'

export function NLSearchBar() {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)
  const [toolsUsed, setToolsUsed] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setAnswer(null)
    setError(null)

    try {
      const res = await api.nlQuery(query.trim())
      setAnswer(res.answer)
      setToolsUsed(res.tools_used)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 429) setError('Too many searches — wait a moment before trying again.')
        else if (err.status === 408) setError('Search timed out. Try a more specific question.')
        else setError('Search failed. Please try again.')
      } else {
        setError('Search failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-full space-y-3">
      <form onSubmit={handleSubmit} className="relative flex items-center">
        <Search
          size={16}
          className="absolute left-3"
          style={{ color: 'var(--muted)' }}
        />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask about the housing market..."
          className="pl-9 h-11 text-sm"
          disabled={loading}
          maxLength={500}
        />
      </form>

      {loading && <Skeleton className="h-12 w-full" />}

      {error && (
        <div
          className="rounded-md px-4 py-3 text-sm"
          style={{ background: 'color-mix(in srgb, var(--accent) 10%, transparent)', color: 'var(--text)' }}
        >
          ⚠️ {error}
        </div>
      )}

      {answer && !loading && (
        <div className="space-y-1">
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text)' }}>
            {answer}
          </p>
          {toolsUsed.length > 0 && (
            <p className="text-xs" style={{ color: 'var(--muted)' }}>
              Used: {toolsUsed.join(', ')}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
