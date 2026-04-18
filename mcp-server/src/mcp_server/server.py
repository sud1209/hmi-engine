from mcp.server.fastmcp import FastMCP

from .db.session import init_db
from .tools.search_houses import search_houses as _search_houses
from .tools.valuation_data import get_valuation_data as _get_valuation_data, get_neighborhood_snapshot as _get_neighborhood_snapshot, get_mortgage_rates as _get_mortgage_rates
from .tools.housing_market import get_housing_market_snapshot as _get_housing_market_snapshot, calculate_roi as _calculate_roi

mcp = FastMCP("housing-market-intelligence")

@mcp.tool()
async def search_houses(
    query: str = None,
    city: str = None,
    state: str = None,
    zip_code: str = None,
    min_price: int = None,
    max_price: int = None,
    property_type: str = None,
    limit: int = 10,
    offset: int = 0
):
    """Search for house listings. Supports address, city, state, zip code, and price filters."""
    return await _search_houses(query, city, state, zip_code, min_price, max_price, property_type, limit, offset)

@mcp.tool()
async def get_valuation_data(zip_code: str = None):
    """Get market valuation trends for a specific zip code."""
    return await _get_valuation_data(zip_code)

@mcp.tool()
async def get_neighborhood_snapshot(zip_code: str):
    """Get a high-level snapshot of a neighborhood (schools, crime, walkability)."""
    return await _get_neighborhood_snapshot(zip_code)

@mcp.tool()
async def get_mortgage_rates():
    """Get current mortgage rates from major lenders."""
    return await _get_mortgage_rates()

@mcp.tool()
async def get_housing_market_snapshot(city: str, state: str):
    """Get a high-level snapshot of a housing market (prices, inventory, days on market)."""
    return await _get_housing_market_snapshot(city, state)

@mcp.tool()
async def calculate_roi(purchase_price: float, monthly_rent: float, annual_expenses: float = 0) -> dict:
    """Calculate expected ROI for a rental property."""
    return await _calculate_roi(purchase_price, monthly_rent, annual_expenses)


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
    mcp.run()
