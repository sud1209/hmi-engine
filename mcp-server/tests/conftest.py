import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from mcp_server.db.models import Base
import mcp_server.db.session as session_module
import mcp_server.tools.search_houses as search_houses_module
import mcp_server.tools.valuation_data as valuation_data_module
import mcp_server.tools.housing_market as housing_market_module
import mcp_server.feeds.news_fetcher as news_fetcher_module


@pytest_asyncio.fixture(autouse=True)
async def override_db_session(monkeypatch):
    """Override DB session with in-memory SQLite for all tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    # Patch both the session module and all tool modules that import AsyncSessionLocal directly
    monkeypatch.setattr(session_module, "AsyncSessionLocal", TestSession)
    monkeypatch.setattr(search_houses_module, "AsyncSessionLocal", TestSession)
    monkeypatch.setattr(valuation_data_module, "AsyncSessionLocal", TestSession)
    monkeypatch.setattr(housing_market_module, "AsyncSessionLocal", TestSession)
    monkeypatch.setattr(news_fetcher_module, "AsyncSessionLocal", TestSession)

    # Seed minimal data so tool functions return non-empty results
    async with TestSession() as session:
        from datetime import date
        from mcp_server.db.models import HouseListing, NeighborhoodTrend, MortgageRate

        session.add(HouseListing(
            id="test-001", address="123 Main St", city="Austin", state="TX",
            zip_code="78701", price=450_000, beds=3.0, baths=2.0, sqft=1800,
            property_type="Single Family", year_built=2010,
            posted_date=date.today(), source="test",
        ))
        session.add(HouseListing(
            id="test-002", address="456 Oak Ave", city="Houston", state="TX",
            zip_code="77001", price=350_000, beds=4.0, baths=3.0, sqft=2200,
            property_type="Single Family", year_built=2015,
            posted_date=date.today(), source="test",
        ))
        session.add(NeighborhoodTrend(
            id="nt-001", zip_code="78701",
            median_listing_price=450_000, median_days_on_market=28,
            inventory_count=150, school_score=8.5, crime_score=3.2,
            walk_score=72.0, updated_date=date.today(),
        ))
        session.add(MortgageRate(
            id="mr-001", term_years=30, rate=6.75,
            type="Fixed", updated_date=date.today(),
        ))
        session.add(MortgageRate(
            id="mr-002", term_years=15, rate=6.10,
            type="Fixed", updated_date=date.today(),
        ))
        await session.commit()

    yield

    await engine.dispose()
