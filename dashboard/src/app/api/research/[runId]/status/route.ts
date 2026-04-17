import { NextRequest, NextResponse } from 'next/server'

const AGENT = process.env.AGENT_API ?? 'http://localhost:8000'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ runId: string }> }
) {
  const { runId } = await params
  try {
    const res = await fetch(`${AGENT}/research/${encodeURIComponent(runId)}/status`)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: 'agent-runner unreachable' }, { status: 502 })
  }
}
