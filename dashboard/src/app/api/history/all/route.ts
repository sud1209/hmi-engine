import { NextResponse } from 'next/server'

const MCP = process.env.MCP_API ?? 'http://localhost:8001'

// Fetches history for all available markets and returns as a market→snapshots map
export async function GET() {
  try {
    // Get rankings to discover all market names
    const rankRes = await fetch(`${MCP}/msa/rankings?metric=median_sale_price&sort=desc&limit=100`)
    const rankings = await rankRes.json() as { market: string }[]
    const markets = ['National', ...rankings.map((r) => r.market)]

    const entries = await Promise.all(
      markets.map(async (m) => {
        const res = await fetch(`${MCP}/history/${encodeURIComponent(m)}?years=5`)
        const data = await res.json()
        return [m, Array.isArray(data) ? data : []] as const
      })
    )
    return NextResponse.json(Object.fromEntries(entries))
  } catch {
    return NextResponse.json({ detail: 'mcp-server unreachable' }, { status: 502 })
  }
}
