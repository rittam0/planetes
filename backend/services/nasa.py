import os
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import time

NASA_BASE = "https://api.nasa.gov/neo/rest/v1"
API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")

async def fetch_asteroid_feed(start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
    if not API_KEY or API_KEY == "DEMO_KEY":
        print("[NASA] No API key configured")
        return None
    url = f"{NASA_BASE}/feed"
    params = {"start_date": start_date, "end_date": end_date, "api_key": API_KEY}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.time()
            resp = await client.get(url, params=params)
            latency = round((time.time() - start) * 1000, 2)
            print(f"[NASA] status={resp.status_code} latency={latency}ms")
            if resp.status_code == 200:
                data = resp.json()
                data["_api_latency_ms"] = latency
                data["_source"] = "nasa"
                return data
            elif resp.status_code == 403:
                print("[NASA] 403 - invalid key or rate limit")
            else:
                print(f"[NASA] Error {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"[NASA] Error: {e}")
    return None
