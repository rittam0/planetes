import os
import httpx
from typing import Optional, List, Dict, Any

KEEPTRACK_BASE = "https://api.keeptrack.space"
API_KEY = os.getenv("KEEPTRACK_API_KEY", "DEMO_KEY")

async def fetch_catalog(limit: int = 100) -> Optional[List[Dict[str, Any]]]:
    if API_KEY == "DEMO_KEY" or not API_KEY or not API_KEY.startswith("kt_"):
        print(f"[KeepTrack] No valid API key. Key present: {bool(API_KEY and API_KEY != 'DEMO_KEY')}")
        return None
    
    url = f"{KEEPTRACK_BASE}/v4/catalog"
    headers = {"X-API-Key": API_KEY}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers, params={"limit": min(limit, 100)})
            print(f"[KeepTrack] Catalog status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    print(f"[KeepTrack] Got {len(data)} objects from catalog")
                    return data
                if isinstance(data, dict):
                    for key in ["data", "objects", "results", "catalog"]:
                        if key in data and isinstance(data[key], list):
                            print(f"[KeepTrack] Got {len(data[key])} objects from catalog (key={key})")
                            return data[key]
                print(f"[KeepTrack] Unexpected response format: {type(data)}")
                return None
            else:
                print(f"[KeepTrack] API error: {resp.status_code} - {resp.text[:200]}")
                return None
    except Exception as e:
        print(f"[KeepTrack] Fetch error: {e}")
        return None

async def fetch_satellite(norad_id: str) -> Optional[Dict[str, Any]]:
    if API_KEY == "DEMO_KEY" or not API_KEY:
        return None
    
    url = f"{KEEPTRACK_BASE}/v4/sats/{norad_id}"
    headers = {"X-API-Key": API_KEY}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                return data if isinstance(data, dict) else None
            else:
                print(f"[KeepTrack] Sat error: {resp.status_code}")
                return None
    except Exception as e:
        print(f"[KeepTrack] Sat fetch error: {e}")
        return None
