import os
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import time

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
            start = time.time()
            resp = await client.get(url, params=params)
            latency = round((time.time() - start) * 1000, 2)
            
            print(f"[NASA] /feed status={resp.status_code} latency={latency}ms")
            
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 403:
                print(f"[NASA] 403 Forbidden - invalid API key or rate limit exceeded")
                return None
            else:
                print(f"[NASA] API error: {resp.status_code} - {resp.text[:200]}")
                return None
    except Exception as e:
        print(f"[NASA] Fetch error: {e}")
        return None

async def fetch_asteroid_detail(asteroid_id: str) -> Optional[Dict[str, Any]]:
    if API_KEY == "DEMO_KEY" or not API_KEY:
        return None
    
    url = f"{NASA_BASE}/neo/{asteroid_id}"
    params = {"api_key": API_KEY}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            return None
    except Exception as e:
        print(f"[NASA] Detail fetch error: {e}")
        return None
