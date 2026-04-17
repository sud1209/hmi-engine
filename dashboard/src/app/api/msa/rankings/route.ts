import { NextRequest, NextResponse } from 'next/server'

const MCP = process.env.MCP_API ?? 'http://localhost:8001'

export async function GET(req: NextRequest) {
  const metric = req.nextUrl.searchParams.get('metric') ?? 'median_sale_price'
  const sort = req.nextUrl.searchParams.get('sort') ?? 'desc'
  try {
    const res = await fetch(`${MCP}/msa/rankings?metric=${encodeURIComponent(metric)}&sort=${sort}`)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: 'mcp-server unreachable' }, { status: 502 })
  }
}
