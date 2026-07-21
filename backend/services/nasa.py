import os
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import time

# Load .env before reading API_KEY
from pathlib import Path
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

NASA_BASE = "https://api.nasa.gov/neo/rest/v1"
API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")

async def fetch_asteroid_feed(start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
    print(f"[NASA] API_KEY present: {bool(API_KEY and API_KEY != 'DEMO_KEY')}")
    if not API_KEY or API_KEY == "DEMO_KEY":
        print("[NASA] No API key configured")
        return None
    
    url = f"{NASA_BASE}/feed"
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "api_key": API_KEY
    }
    
    print(f"[NASA] Requesting: {url} | dates: {start_date} to {end_date}")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.time()
            resp = await client.get(url, params=params)
            latency = round((time.time() - start) * 1000, 2)
            print(f"[NASA] Response: status={resp.status_code}, latency={latency}ms")
            
            if resp.status_code == 200:
                data = resp.json()
                neo_count = len(data.get("near_earth_objects", {}))
                total_neos = sum(len(v) for v in data.get("near_earth_objects", {}).values())
                print(f"[NASA] Success: {neo_count} dates, {total_neos} total NEOs")
                data["_api_latency_ms"] = latency
                data["_source"] = "nasa"
                return data
            elif resp.status_code == 403:
                print(f"[NASA] 403 Forbidden: Invalid key or rate limit")
                print(f"[NASA] Body: {resp.text[:200]}")
            elif resp.status_code == 400:
                print(f"[NASA] 400 Bad Request: Invalid date range")
                print(f"[NASA] Body: {resp.text[:200]}")
            else:
                print(f"[NASA] Error {resp.status_code}: {resp.text[:200]}")
    except httpx.TimeoutException:
        print("[NASA] Timeout after 30s")
    except httpx.ConnectError as e:
        print(f"[NASA] Connection error: {e}")
    except Exception as e:
        print(f"[NASA] Unexpected exception {type(e).__name__}: {e}")
    
    return None
