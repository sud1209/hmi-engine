from datetime import date
from sqlalchemy import JSON, Column, Date, DateTime, Integer, String, Float, Text, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class HouseListing(Base):
    __tablename__ = "house_listings"

    id = Column(String, primary_key=True)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    zip_code = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    beds = Column(Float, nullable=False)
    baths = Column(Float, nullable=False)
    sqft = Column(Integer, nullable=False)
    property_type = Column(String, nullable=False)
    year_built = Column(Integer, nullable=True)
    lot_size = Column(Float, nullable=True)
    posted_date = Column(Date, nullable=False)
    source = Column(String, nullable=False)
    description = Column(String, nullable=True)


class NeighborhoodTrend(Base):
    __tablename__ = "neighborhood_trends"

    id = Column(String, primary_key=True)
    zip_code = Column(String, nullable=False)
    median_listing_price = Column(Integer, nullable=False)
    median_days_on_market = Column(Integer, nullable=False)
    inventory_count = Column(Integer, nullable=False)
    school_score = Column(Float, nullable=True)
    crime_score = Column(Float, nullable=True)
    walk_score = Column(Float, nullable=True)
    updated_date = Column(Date, nullable=False)


class MortgageRate(Base):
    __tablename__ = "mortgage_rates"

    id = Column(String, primary_key=True)
    term_years = Column(Integer, nullable=False)
    rate = Column(Float, nullable=False)
    type = Column(String, nullable=False)  # "Fixed", "ARM"
    updated_date = Column(Date, nullable=False)
    updated_at = Column(DateTime, nullable=True, server_default=func.now(), onupdate=func.now())


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(String, primary_key=True)
    headline = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    source = Column(String, nullable=True)
    url = Column(String, nullable=True, unique=True)
    relevance_score = Column(String, nullable=True)  # "high", "medium", "low"
    market = Column(String, nullable=True)            # None = applies to all markets
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, nullable=False, server_default=func.now())


class KPISnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id = Column(String, primary_key=True)
    market = Column(String, nullable=False)
    kpis = Column(JSON, nullable=False)   # {"avg_list_price": "$820,000", ...}
    as_of_date = Column(Date, nullable=False)
    ingested_at = Column(DateTime, nullable=False, server_default=func.now())


class MarketHistorySnapshot(Base):
    """Monthly market history per MSA — powers visualization tabs."""
    __tablename__ = "market_history_snapshots"

    id = Column(String, primary_key=True)              # "{market}-{month.isoformat()}"
    market = Column(String, nullable=False, index=True)
    month = Column(Date, nullable=False, index=True)   # first day of the month

    # Absolute metrics (shown as-is)
    median_dom = Column(Integer, nullable=True)        # days on market
    months_supply = Column(Float, nullable=True)       # supply in months
    mortgage_rate_30yr = Column(Float, nullable=True)  # %
    price_per_sqft = Column(Integer, nullable=True)    # $

    # Raw counts (YoY % computed at query time)
    active_listings = Column(Integer, nullable=True)
    median_sale_price = Column(Integer, nullable=True)
    sales_volume = Column(Integer, nullable=True)
    new_listings = Column(Integer, nullable=True)
