import { NextRequest, NextResponse } from 'next/server'

const MCP = process.env.MCP_API ?? 'http://localhost:8001'

export async function GET(req: NextRequest) {
  const market = req.nextUrl.searchParams.get('market') ?? 'National'
  try {
    const res = await fetch(`${MCP}/dashboard?market=${encodeURIComponent(market)}`)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: 'mcp-server unreachable' }, { status: 502 })
  }
}
