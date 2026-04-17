'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useResearchStatus } from '@/hooks/useResearchStatus'
import { api, ApiError } from '@/lib/api'
import ReactMarkdown from 'react-markdown'

type PanelState = 'idle' | 'awaiting_approval' | 'running' | 'complete' | 'error'

export function ResearchPanel() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [runId, setRunId] = useState<string | null>(null)
  const [plan, setPlan] = useState<string[]>([])
  const [panelState, setPanelState] = useState<PanelState>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const { data: statusData } = useResearchStatus(
    panelState === 'running' ? runId : null
  )

  // Sync panel state from polling
  if (panelState === 'running' && statusData) {
    if (statusData.status === 'complete') setPanelState('complete')
    else if (statusData.status === 'error') {
      setPanelState('error')
      setErrorMsg(statusData.error ?? 'Pipeline failed.')
    } else if (statusData.status === 'rejected') {
      setPanelState('idle')
    }
  }

  async function handleStart() {
    if (!query.trim()) return
    setSubmitting(true)
    try {
      const run = await api.startResearch(query.trim())
      setRunId(run.run_id)
      setPlan(run.plan ?? [])
      setPanelState('awaiting_approval')
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Failed to start research.')
      setPanelState('error')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleApprove(approved: boolean) {
    if (!runId) return
    try {
      await api.approveResearch(runId, approved)
      setPanelState(approved ? 'running' : 'idle')
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Approval failed.')
      setPanelState('error')
    }
  }

  function reset() {
    setRunId(null)
    setPlan([])
    setPanelState('idle')
    setErrorMsg('')
    setQuery('')
  }

  const report = statusData?.result?.report?.report_markdown
  const kpis = statusData?.result?.dashboard?.kpis

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <button
          className="flex items-center gap-2 text-sm font-semibold w-full text-left py-3"
          style={{ color: 'var(--text)' }}
        >
          {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          AI Research
        </button>
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div
          className="rounded-lg p-4 space-y-4"
          style={{ background: 'var(--surface)', border: '1px solid var(--border-color)' }}
        >
          {/* IDLE */}
          {panelState === 'idle' && (
            <div className="flex gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleStart()}
                placeholder="Research topic, e.g. Austin rental market outlook"
                className="text-sm"
                disabled={submitting}
                maxLength={500}
              />
              <Button onClick={handleStart} disabled={submitting || !query.trim()} size="sm">
                {submitting ? 'Starting…' : 'Run Research'}
              </Button>
            </div>
          )}

          {/* AWAITING APPROVAL */}
          {panelState === 'awaiting_approval' && (
            <div className="space-y-4">
              <div>
                <p className="text-sm font-medium mb-2" style={{ color: 'var(--text)' }}>
                  Research Plan
                </p>
                <ul className="space-y-1">
                  {plan.map((step, i) => (
                    <li key={i} className="text-sm flex gap-2" style={{ color: 'var(--muted)' }}>
                      <span style={{ color: 'var(--accent)' }}>•</span> {step}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => handleApprove(true)}>✓ Approve</Button>
                <Button size="sm" variant="outline" onClick={() => handleApprove(false)}>
                  ✗ Reject
                </Button>
              </div>
            </div>
          )}

          {/* RUNNING */}
          {panelState === 'running' && (
            <div className="space-y-3">
              <Progress value={undefined} className="h-1" />
              <p className="text-sm" style={{ color: 'var(--muted)' }}>
                Pipeline running — this takes ~30 seconds…
              </p>
            </div>
          )}

          {/* COMPLETE */}
          {panelState === 'complete' && report && (
            <div className="space-y-4">
              <div
                className="max-h-96 overflow-y-auto rounded p-4 text-sm leading-relaxed"
                style={{ background: 'var(--bg)', color: 'var(--text)' }}
              >
                <ReactMarkdown>{report}</ReactMarkdown>
              </div>
              {kpis && (
                <div className="grid grid-cols-3 gap-3 text-sm">
                  {Object.entries(kpis).map(([k, v]) => (
                    <div key={k} className="text-center">
                      <p style={{ color: 'var(--muted)' }} className="text-xs">{k}</p>
                      <p style={{ color: 'var(--text)' }} className="font-semibold">{String(v)}</p>
                    </div>
                  ))}
                </div>
              )}
              <Button size="sm" variant="outline" onClick={reset}>Run another</Button>
            </div>
          )}

          {/* ERROR */}
          {panelState === 'error' && (
            <Alert variant="destructive">
              <AlertDescription className="text-sm">{errorMsg}</AlertDescription>
              <Button size="sm" variant="outline" className="mt-2" onClick={reset}>
                Try again
              </Button>
            </Alert>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
