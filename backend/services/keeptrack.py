import os
import httpx
from typing import Optional, List, Dict, Any
import time

KEEPTRACK_BASE = "https://api.keeptrack.space"
API_KEY = os.getenv("KEEPTRACK_API_KEY", "DEMO_KEY")

async def fetch_catalog(limit: int = 100) -> Optional[List[Dict[str, Any]]]:
    if API_KEY == "DEMO_KEY" or not API_KEY or not API_KEY.startswith("kt_"):
        print(f"[KeepTrack] No valid API key. Key present: {bool(API_KEY and API_KEY != 'DEMO_KEY')}")
        return None
    
    urls_to_try = [
        f"{KEEPTRACK_BASE}/v4/catalog",
        f"{KEEPTRACK_BASE}/v2/catalog/latest",
    ]
    
    headers = {"X-API-Key": API_KEY}
    
    for url in urls_to_try:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                start = time.time()
                resp = await client.get(url, headers=headers, params={"limit": min(limit, 100)})
                latency = round((time.time() - start) * 1000, 2)
                
                print(f"[KeepTrack] {url} status={resp.status_code} latency={latency}ms")
                
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        print(f"[KeepTrack] Got {len(data)} objects from {url}")
                        return data
                    if isinstance(data, dict):
                        for key in ["data", "objects", "results", "catalog", "sats"]:
                            if key in data and isinstance(data[key], list):
                                print(f"[KeepTrack] Got {len(data[key])} objects from {url} (key={key})")
                                return data[key]
                    print(f"[KeepTrack] Unexpected format from {url}: {type(data)}")
                elif resp.status_code == 404:
                    print(f"[KeepTrack] {url} not found, trying next...")
                    continue
                else:
                    print(f"[KeepTrack] {url} error: {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            print(f"[KeepTrack] {url} exception: {e}")
    
    return None

async def fetch_satellite(norad_id: str) -> Optional[Dict[str, Any]]:
    if API_KEY == "DEMO_KEY" or not API_KEY:
        return None
    
    url = f"{KEEPTRACK_BASE}/v4/sats/{norad_id}"
    headers = {"X-API-Key": API_KEY}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.time()
            resp = await client.get(url, headers=headers)
            latency = round((time.time() - start) * 1000, 2)
            
            print(f"[KeepTrack] /v4/sats/{norad_id} status={resp.status_code} latency={latency}ms")
            
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

async def fetch_tle(norad_id: str) -> Optional[Dict[str, Any]]:
    if API_KEY == "DEMO_KEY" or not API_KEY:
        return None
    
    url = f"{KEEPTRACK_BASE}/v4/sat/{norad_id}/tle"
    headers = {"X-API-Key": API_KEY}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            return None
    except Exception as e:
        print(f"[KeepTrack] TLE fetch error: {e}")
        return None
