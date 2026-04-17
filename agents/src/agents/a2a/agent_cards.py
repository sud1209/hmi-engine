from agents.a2a.protocol import AgentCard

RESEARCHER_ANALYST_CARD = AgentCard(
    agent_id="researcher_analyst",
    name="Housing Researcher & Analyst",
    role="Property data acquisition and valuation analysis using MCP tools and Python sandbox",
    capabilities=["mcp_tool_use", "real_estate_scraping", "computer_use", "valuation_analysis", "roi_calculation", "code_execution"],
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "zip_codes": {"type": "array", "items": {"type": "string"}},
            "analysis_type": {"type": "string"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "listings": {"type": "array"},
            "market_snapshot": {"type": "object"},
            "valuation_insights": {"type": "object"},
            "roi_metrics": {"type": "object"}
        }
    }
)

WRITER_CARD = AgentCard(
    agent_id="writer",
    name="Real Estate Writer",
    role="Synthesis of property research and analysis into real estate reports",
    capabilities=["report_synthesis", "real_estate_markdown"],
    input_schema={
        "type": "object",
        "properties": {
            "property_data": {"type": "object"},
            "analysis_results": {"type": "object"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "report_markdown": {"type": "string"},
            "summary": {"type": "string"}
        }
    }
)

NEWS_ANALYST_CARD = AgentCard(
    agent_id="news_analyst",
    name="Housing News Analyst",
    role="Research and analysis of real estate news from Realtor.com, Zillow, and Redfin",
    capabilities=["news_scraping", "sentiment_analysis", "trend_forecasting"],
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "sources": {"type": "array", "items": {"type": "string"}}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "news_summary": {"type": "string"},
            "market_sentiment": {"type": "string"},
            "articles": {"type": "array"}
        }
    }
)

AGENT_CARDS = {
    "researcher_analyst": RESEARCHER_ANALYST_CARD,
    "writer": WRITER_CARD,
    "news_analyst": NEWS_ANALYST_CARD,
}
