import asyncio
import pandas as pd
from core.external_data import ExternalDataConnector

async def verify_fetch():
    print("Initializing ExternalDataConnector...")
    connector = ExternalDataConnector()
    
    industry = "Retail"
    location = "13000" # Tokyo
    
    print(f"Fetching statistics for {industry} in {location}...")
    
    # 1. Industry Stats
    stats = connector.get_industry_statistics(industry)
    if stats:
        print(f"✅ Industry Stats Acquired: {stats.industry_name}")
        print(f"   Establishments: {stats.establishment_count} " if stats.establishment_count else "   Establishments: N/A")
    else:
        print("❌ Industry Stats Failed")

    # 2. Regional Potential
    regional = connector.get_regional_market_potential(location, industry)
    if regional:
        print(f"✅ Regional Data Acquired: {len(regional)} items")
    else:
        print("❌ Regional Data Failed")

if __name__ == "__main__":
    asyncio.run(verify_fetch())
