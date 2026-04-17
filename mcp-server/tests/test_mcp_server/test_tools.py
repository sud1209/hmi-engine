import pytest
from mcp_server.tools.search_houses import search_houses
from mcp_server.tools.valuation_data import (
    get_valuation_data,
    get_neighborhood_snapshot,
    get_mortgage_rates,
)
from mcp_server.tools.housing_market import (
    get_housing_market_snapshot,
    calculate_roi,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_search_houses_returns_listings():
    result = await search_houses(query="3 bed house", limit=5)
    assert "listings" in result
    assert isinstance(result["listings"], list)
    assert result["total"] >= 0


@pytest.mark.asyncio
async def test_search_houses_city_filter():
    result = await search_houses(city="Austin", state="TX", limit=3)
    assert "listings" in result
    assert len(result["listings"]) > 0
    for listing in result["listings"]:
        assert listing["city"] == "Austin"


@pytest.mark.asyncio
async def test_search_houses_listing_structure():
    result = await search_houses(limit=1)
    assert "listings" in result
    assert len(result["listings"]) > 0
    listing = result["listings"][0]
    assert "id" in listing
    assert "address" in listing
    assert "city" in listing
    assert "state" in listing
    assert "zip_code" in listing
    assert "price" in listing
    assert "beds" in listing
    assert "baths" in listing
    assert "sqft" in listing
    assert "property_type" in listing
    assert "year_built" in listing
    assert "posted_date" in listing
    assert "source" in listing


@pytest.mark.asyncio
async def test_get_valuation_data_structure():
    result = await get_valuation_data(zip_code="78701")
    assert isinstance(result, list)
    assert len(result) > 0
    row = result[0]
    assert "zip_code" in row
    assert "median_listing_price" in row


@pytest.mark.asyncio
async def test_get_neighborhood_snapshot_structure():
    result = await get_neighborhood_snapshot(zip_code="78701")
    assert "error" not in result
    assert "zip_code" in result
    assert "school_score" in result
    assert "walk_score" in result


@pytest.mark.asyncio
async def test_get_mortgage_rates_returns_rates():
    result = await get_mortgage_rates()
    assert isinstance(result, list)
    assert len(result) > 0
    rate = result[0]
    assert "term_years" in rate
    assert "rate" in rate
    assert "type" in rate
    assert "updated_date" in rate
    assert isinstance(rate["rate"], (int, float))


@pytest.mark.asyncio
async def test_get_housing_market_snapshot_national():
    result = await get_housing_market_snapshot()
    assert "total_listings" in result
    assert "average_median_price" in result
    assert "latest_mortgage_rate" in result
    assert "as_of_date" in result


@pytest.mark.asyncio
async def test_get_housing_market_snapshot_city_filter():
    result = await get_housing_market_snapshot(city_filter="Austin")
    assert "total_listings" in result
    assert "average_median_price" in result
    assert "latest_mortgage_rate" in result


@pytest.mark.asyncio
async def test_calculate_roi_positive_cash_flow():
    result = await calculate_roi(
        purchase_price=400_000,
        monthly_rent=2_800,
        property_tax_annual=6_000,
        insurance_annual=1_200,
        maintenance_annual=2_000,
    )
    assert "net_operating_income" in result
    assert "annual_roi_percentage" in result
    assert result["net_operating_income"] > 0
    assert result["annual_roi_percentage"] > 0


@pytest.mark.asyncio
async def test_calculate_roi_negative_cash_flow():
    result = await calculate_roi(
        purchase_price=1_200_000,
        monthly_rent=2_000,
        property_tax_annual=20_000,
        insurance_annual=4_000,
        maintenance_annual=8_000,
    )
    assert "net_operating_income" in result
    assert "annual_roi_percentage" in result
    assert result["net_operating_income"] < 0
