import { NextRequest, NextResponse } from 'next/server'

const AGENT = process.env.AGENT_API ?? 'http://localhost:8000'

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ runId: string }> }
) {
  const { runId } = await params
  try {
    const body = await req.json()
    const res = await fetch(`${AGENT}/research/${encodeURIComponent(runId)}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: 'agent-runner unreachable' }, { status: 502 })
  }
}
