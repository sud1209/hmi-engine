# HMI Engine — API Reference

All endpoints are accessed through the Caddy reverse proxy. In dev: `http://localhost`.

- MCP server: `http://localhost/api/...`
- Agent runner: `http://localhost/agent/...`

For direct access (bypassing Caddy): mcp-server at `:8001`, agent-runner at `:8000`.

---

## MCP Server (`/api`)

### `GET /api/health`

Health check. Always public.

**Response 200:**
```json
{"status": "ok", "version": "0.1.0", "service": "mcp-server"}
```

---

### `GET /api/dashboard`

Dashboard KPIs, news, and mortgage rate data for a market.

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| `market` | string | `"National"` | MSA name or `"National"` |

**Rate limit:** 60/min (no auth required)

**Response 200:**
```json
{
  "kpis": {
    "avg_list_price": "$425,000",
    "active_listings": "1,234",
    "rate_30yr_fixed": "6.82%",
    "median_dom": "28 days",
    "price_per_sqft": "$210",
    "new_listings_30d": "156",
    "price_reductions": "11%",
    "months_supply": "2.4 mo"
  },
  "recent_news": [
    {
      "headline": "Housing Inventory Rises Nationally",
      "summary": "Active listings up 8% month-over-month.",
      "source": "HMI Engine",
      "relevance_score": "high"
    }
  ],
  "market_snapshot": {
    "total_listings": 1234,
    "average_median_price": 425000,
    "latest_mortgage_rate": 6.82,
    "as_of_date": "2026-04-17"
  },
  "mortgage_rates": [
    {"term_years": 30, "rate": 6.82, "rate_type": "fixed"},
    {"term_years": 15, "rate": 6.12, "rate_type": "fixed"}
  ]
}
```

**KPI data source priority:**
1. Latest `KPISnapshot` row for the market (pipeline push)
2. Computed on-the-fly from `HouseListing` + `NeighborhoodTrend` tables

---

### `GET /api/history/{market}`

Monthly time-series for a market (used by Trends and Historical visualization tabs).

**Path params:**
| Param | Type | Description |
|---|---|---|
| `market` | string | MSA name or `"National"` |

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| `years` | int | `5` | Number of years of history |

**Response 200:** Array sorted by `month` ascending.
```json
[
  {
    "market": "Austin",
    "month": "2021-04-01",
    "median_dom": 14,
    "months_supply": 0.8,
    "mortgage_rate_30yr": 3.12,
    "price_per_sqft": 248,
    "active_listings": 1200,
    "median_sale_price": 385000,
    "sales_volume": 890,
    "new_listings": 950,
    "yoy_active_listings": 12.4,
    "yoy_sale_price": 28.6,
    "yoy_sales_volume": -3.1,
    "yoy_new_listings": 8.9
  }
]
```

YoY fields (`yoy_*`) are computed server-side: `(current - prior_year) / prior_year * 100`. Returns `null` if no prior-year row exists.

---

### `GET /api/msa/rankings`

Latest snapshot value for all markets, sorted by metric (used by Rankings tab).

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| `metric` | string | `median_sale_price` | One of 8 KPI fields (see below) |
| `sort` | string | `desc` | `asc` or `desc` |
| `limit` | int | `100` | Max markets to return |

**Valid metric values:**
- YoY metrics (returns % change): `active_listings`, `median_sale_price`, `sales_volume`, `new_listings`
- Absolute metrics (returns raw value): `median_dom`, `months_supply`, `mortgage_rate_30yr`, `price_per_sqft`

**Response 200:**
```json
[
  {
    "market": "Austin",
    "value": 28.6,
    "rank": 1
  }
]
```

For YoY metrics, `value` is the YoY % change. For absolute metrics, `value` is the raw figure.

---

### `POST /api/query`

Natural language query over housing data using Haiku tool-use.

**Auth:** JWT required (rate: 10/min); anon allowed (rate: 3/min).

**Request body:**
```json
{"query": "What is the average price per sqft in Austin vs Denver?"}
```

**Constraints:**
- `query` max 500 chars
- Rejected (400) if query contains SQL keywords: `DROP`, `DELETE`, `INSERT`, `UPDATE`, `EXEC`

**Response 200:**
```json
{
  "answer": "Austin averages $248/sqft and Denver averages $312/sqft based on current listings data.",
  "tools_used": ["search_houses", "get_housing_market_snapshot"]
}
```

**Error responses:**
- `400` — query too long or contains rejected keywords
- `408` — query timed out (15s limit)
- `429` — rate limit exceeded

**Internal behavior:** Haiku tool-use loop, max 3 rounds, read-only tool whitelist (`search_houses`, `get_valuation_data`, `get_neighborhood_snapshot`, `get_mortgage_rates`, `get_housing_market_snapshot`). Final synthesis `max_tokens=300`.

---

### `POST /api/tools/call/{tool_name}`

Direct tool call. Protected (JWT required). Rate: 20/min.

**Path params:**
| Param | Description |
|---|---|
| `tool_name` | One of the 6 MCP tools (see below) |

**Request body:** Tool-specific parameters (see tool schemas below).

**Response 200:** Tool result object.

**Available tools:**

| Tool | Key Parameters |
|---|---|
| `search_houses` | `query`, `city`, `state`, `zip_code`, `min_price`, `max_price`, `property_type`, `limit`, `offset` |
| `get_valuation_data` | `zip_code` |
| `get_neighborhood_snapshot` | `zip_code` |
| `get_mortgage_rates` | (none) |
| `get_housing_market_snapshot` | `city_filter` |
| `calculate_roi` | `purchase_price`, `monthly_rent`, `property_tax_annual`, `insurance_annual`, `maintenance_annual` |

---

### `POST /api/ingest/kpis`

Push KPI snapshot for a market. Requires API key (`X-API-Key` header).

**Request body:**
```json
{
  "market": "National",
  "kpis": {
    "avg_list_price": "$425,000",
    "active_listings": "1,234",
    "rate_30yr_fixed": "6.82%",
    "median_dom": "28 days",
    "price_per_sqft": "$210",
    "new_listings_30d": "156",
    "price_reductions": "11%",
    "months_supply": "2.4 mo"
  },
  "as_of_date": "2026-04-17"
}
```

**Response 200:**
```json
{"status": "ok", "market": "National", "as_of_date": "2026-04-17"}
```

---

### `GET /api/metrics`

Prometheus metrics. Public.

Returns text/plain Prometheus exposition format. Key metrics:
- `http_requests_total{method, endpoint, status_code}`
- `http_request_duration_seconds{method, endpoint}`
- `hmi_feed_fetch_total{feed, status}`
- `hmi_research_total{status}`
- `hmi_hitl_approval_total{outcome}`

---

## Agent Runner (`/agent`)

### `GET /agent/health`

**Response 200:**
```json
{"status": "ok", "version": "0.1.0"}
```

---

### `POST /agent/research`

Start a research run. Returns immediately with a plan for approval.

**Request body:**
```json
{"query": "housing market in Austin Texas"}
```

**Constraints:** `query` min 3 chars, max 500 chars.

**Response 200:**
```json
{
  "run_id": "a3f7c1b2-...",
  "status": "awaiting_approval",
  "plan": [
    "Collect housing listings, market data, and mortgage rates for Austin",
    "Analyze price trends, inventory levels, and investment metrics",
    "Research recent Austin housing market news"
  ]
}
```

**What happens internally:**
1. `graph.ainvoke(initial_state, {thread_id: run_id})`
2. Supervisor decomposes query, writes `research_plan` to state, returns
3. Run registered in `_runs` dict with status `awaiting_approval`

---

### `GET /agent/research/{run_id}/status`

Poll run status.

**Path params:** `run_id` — UUID from `POST /research`

**Response 200:**
```json
{
  "run_id": "a3f7c1b2-...",
  "status": "complete",
  "plan": ["..."],
  "result": {
    "report": {
      "report_markdown": "# Austin Housing Market Report\n\n## Executive Summary\n..."
    },
    "dashboard": {
      "kpis": {
        "national": {
          "mortgage_rate": 6.82,
          "avg_median_price": 425000,
          "market_status": "Low Inventory"
        },
        "metro_specific": {
          "sample_size": 47,
          "avg_price": 512000,
          "estimated_roi": 4.2
        }
      }
    },
    "messages": [...]
  },
  "error": null
}
```

**Status values:**
| Status | Description |
|---|---|
| `awaiting_approval` | Plan created, waiting for human approval |
| `running` | Pipeline executing in background |
| `complete` | Pipeline finished; `result` populated |
| `rejected` | User rejected the plan |
| `error` | Pipeline failed; `error` populated |

**Run TTL:** Entries are deleted from the registry 60 minutes after reaching a terminal status.

---

### `POST /agent/research/{run_id}/approve`

Approve or reject a research plan.

**Path params:** `run_id`

**Request body:**
```json
{"approved": true}
```
or
```json
{"approved": false}
```

**Response 200 (approved):**
```json
{"run_id": "a3f7c1b2-...", "status": "running"}
```

**Response 200 (rejected):**
```json
{"run_id": "a3f7c1b2-...", "status": "rejected"}
```

**Error responses:**
- `404` — run_id not found (may have expired)
- `409` — run is not in `awaiting_approval` status

**What happens on approval:** `asyncio.create_task(_run_to_completion(run_id, config))` is called. The graph resumes from the `MemorySaver` checkpoint using the same `thread_id`, supervisor sees `is_approved=True` and routes to agents.

---

## Error Format

All endpoints return errors in FastAPI default format:

```json
{
  "detail": "Run 'abc123' not found"
}
```

Rate limit errors (from slowapi):
```json
{
  "error": "Rate limit exceeded: 10 per 1 minute"
}
```
