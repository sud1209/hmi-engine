from typing import List, Optional
from sqlalchemy import select, func, and_
from ..db.models import HouseListing
from ..db.session import AsyncSessionLocal

async def search_houses(
    query: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    property_type: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
):
    async with AsyncSessionLocal() as session:
        stmt = select(HouseListing)
        filters = []
        
        if query:
            filters.append(HouseListing.address.ilike(f"%{query}%"))
        if city:
            filters.append(HouseListing.city == city)
        if state:
            filters.append(HouseListing.state == state)
        if zip_code:
            filters.append(HouseListing.zip_code == zip_code)
        if min_price:
            filters.append(HouseListing.price >= min_price)
        if max_price:
            filters.append(HouseListing.price <= max_price)
        if property_type:
            filters.append(HouseListing.property_type == property_type)
            
        if filters:
            stmt = stmt.where(and_(*filters))
            
        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.execute(count_stmt)
        total = total.scalar()
        
        # Get results
        stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        houses = result.scalars().all()
        
        return {
            "total": total,
            "listings": [
                {
                    "id": h.id,
                    "address": h.address,
                    "city": h.city,
                    "state": h.state,
                    "zip_code": h.zip_code,
                    "price": h.price,
                    "beds": h.beds,
                    "baths": h.baths,
                    "sqft": h.sqft,
                    "property_type": h.property_type,
                    "year_built": h.year_built,
                    "posted_date": h.posted_date.isoformat(),
                    "source": h.source
                } for h in houses
            ]
        }
