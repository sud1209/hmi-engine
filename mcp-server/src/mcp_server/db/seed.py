import json
import os
import asyncio
from datetime import datetime
from sqlalchemy import select
from .models import HouseListing, NeighborhoodTrend, MortgageRate, MarketHistorySnapshot
from .session import AsyncSessionLocal, init_db

async def seed_data():
    # Initialize the database schema
    await init_db()
    
    async with AsyncSessionLocal() as session:
        # Seed House Listings
        houses_path = "data/seed/house_listings.json"
        if os.path.exists(houses_path):
            with open(houses_path, "r") as f:
                houses_data = json.load(f)
                for item in houses_data:
                    res = await session.execute(select(HouseListing).where(HouseListing.id == item["id"]))
                    if res.scalar() is None:
                        item["posted_date"] = datetime.strptime(item["posted_date"], "%Y-%m-%d").date()
                        session.add(HouseListing(**item))
        
        # Seed Neighborhood Trends
        trends_path = "data/seed/neighborhood_trends.json"
        if os.path.exists(trends_path):
            with open(trends_path, "r") as f:
                trends_data = json.load(f)
                for item in trends_data:
                    res = await session.execute(select(NeighborhoodTrend).where(NeighborhoodTrend.id == item["id"]))
                    if res.scalar() is None:
                        item["updated_date"] = datetime.strptime(item["updated_date"], "%Y-%m-%d").date()
                        session.add(NeighborhoodTrend(**item))
        
        # Seed Mortgage Rates
        rates_path = "data/seed/mortgage_rates.json"
        if os.path.exists(rates_path):
            with open(rates_path, "r") as f:
                rates_data = json.load(f)
                for item in rates_data:
                    res = await session.execute(select(MortgageRate).where(MortgageRate.id == item["id"]))
                    if res.scalar() is None:
                        item["updated_date"] = datetime.strptime(item["updated_date"], "%Y-%m-%d").date()
                        session.add(MortgageRate(**item))
        
        # Seed Market History (visualization tabs)
        history_path = "data/seed/market_history.json"
        if os.path.exists(history_path):
            with open(history_path, "r") as f:
                history_data = json.load(f)
            for item in history_data:
                res = await session.execute(
                    select(MarketHistorySnapshot).where(MarketHistorySnapshot.id == item["id"])
                )
                if res.scalar() is None:
                    item["month"] = datetime.strptime(item["month"], "%Y-%m-%d").date()
                    session.add(MarketHistorySnapshot(**item))

        await session.commit()
        print("Housing database seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_data())
