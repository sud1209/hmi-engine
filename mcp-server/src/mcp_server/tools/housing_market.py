from typing import Optional
from sqlalchemy import select, func
from datetime import date
from ..db.models import HouseListing, NeighborhoodTrend, MortgageRate
from ..db.session import AsyncSessionLocal

async def get_housing_market_snapshot(
    city_filter: Optional[str] = None,
    as_of_date: Optional[date] = None
):
    async with AsyncSessionLocal() as session:
        # Total listings
        listing_stmt = select(func.count(HouseListing.id))
        if city_filter:
            listing_stmt = listing_stmt.where(HouseListing.city == city_filter)
        total_listings = await session.execute(listing_stmt)
        total_listings = total_listings.scalar()
        
        # Average median price
        price_stmt = select(func.avg(NeighborhoodTrend.median_listing_price))
        avg_price = await session.execute(price_stmt)
        avg_price = avg_price.scalar() or 0
        
        # Get latest mortgage rate
        mortgage_stmt = select(MortgageRate).order_by(MortgageRate.updated_date.desc()).limit(1)
        mortgage_res = await session.execute(mortgage_stmt)
        latest_mortgage = mortgage_res.scalar_one_or_none()
        
        return {
            "total_listings": total_listings,
            "average_median_price": int(avg_price),
            "latest_mortgage_rate": latest_mortgage.rate if latest_mortgage else 0,
            "as_of_date": (as_of_date or date.today()).isoformat()
        }

async def calculate_roi(
    purchase_price: int,
    monthly_rent: int,
    property_tax_annual: int,
    insurance_annual: int,
    maintenance_annual: int
):
    """Calculates basic annual ROI for a property."""
    annual_income = monthly_rent * 12
    annual_expenses = property_tax_annual + insurance_annual + maintenance_annual
    net_operating_income = annual_income - annual_expenses
    roi = (net_operating_income / purchase_price) * 100
    
    return {
        "net_operating_income": net_operating_income,
        "annual_roi_percentage": round(roi, 2)
    }
