from typing import Optional
from sqlalchemy import select
from ..db.models import NeighborhoodTrend, MortgageRate
from ..db.session import AsyncSessionLocal

async def get_valuation_data(
    zip_code: Optional[str] = None
):
    async with AsyncSessionLocal() as session:
        stmt = select(NeighborhoodTrend)
        if zip_code:
            stmt = stmt.where(NeighborhoodTrend.zip_code == zip_code)
            
        result = await session.execute(stmt)
        trends = result.scalars().all()
        
        return [
            {
                "id": t.id,
                "zip_code": t.zip_code,
                "median_listing_price": t.median_listing_price,
                "median_days_on_market": t.median_days_on_market,
                "inventory_count": t.inventory_count,
                "updated_date": t.updated_date.isoformat()
            } for t in trends
        ]
        
async def get_neighborhood_snapshot(
    zip_code: str
):
    async with AsyncSessionLocal() as session:
        stmt = select(NeighborhoodTrend).where(NeighborhoodTrend.zip_code == zip_code)
        result = await session.execute(stmt)
        trend = result.scalar_one_or_none()
        
        if not trend:
            return {"error": f"No data found for zip code {zip_code}"}
            
        return {
            "zip_code": trend.zip_code,
            "school_score": trend.school_score,
            "crime_score": trend.crime_score,
            "walk_score": trend.walk_score,
            "median_price": trend.median_listing_price,
            "market_velocity": "High" if trend.median_days_on_market < 30 else "Normal"
        }

async def get_mortgage_rates():
    async with AsyncSessionLocal() as session:
        stmt = select(MortgageRate).order_by(MortgageRate.updated_date.desc())
        result = await session.execute(stmt)
        rates = result.scalars().all()
        
        return [
            {
                "term_years": r.term_years,
                "rate": r.rate,
                "type": r.type,
                "updated_date": r.updated_date.isoformat()
            } for r in rates
        ]
