import os
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

NASA_BASE = "https://api.nasa.gov/neo/rest/v1"
API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")

async def fetch_asteroid_feed(start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
    if API_KEY == "DEMO_KEY" or not API_KEY:
        return None
    
    url = f"{NASA_BASE}/feed"
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "api_key": API_KEY
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"[NASA] API error: {resp.status_code} - {resp.text[:200]}")
                return None
    except Exception as e:
        print(f"[NASA] Fetch error: {e}")
        return None
