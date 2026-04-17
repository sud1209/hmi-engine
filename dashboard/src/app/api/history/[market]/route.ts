import { NextRequest, NextResponse } from 'next/server'

const MCP = process.env.MCP_API ?? 'http://localhost:8001'

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ market: string }> }
) {
  const { market } = await params
  const years = req.nextUrl.searchParams.get('years') ?? '5'
  try {
    const res = await fetch(
      `${MCP}/history/${encodeURIComponent(market)}?years=${years}`
    )
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: 'mcp-server unreachable' }, { status: 502 })
  }
}
