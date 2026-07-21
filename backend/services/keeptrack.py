import os
import httpx
import asyncio
from typing import Optional, List, Dict, Any
import time
from pathlib import Path
from dotenv import load_dotenv

# Load .env before reading API_KEY
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

KEEPTRACK_BASE = "https://api.keeptrack.space"
API_KEY = os.getenv("KEEPTRACK_API_KEY", "DEMO_KEY")

# Tested working NORAD IDs
KNOWN_SATELLITES = [
    25544, 20580, 48274, 46826, 46827, 46828, 46829, 46830,
    25560, 25994, 27453, 28654, 33591, 43013, 41308, 41942,
    43178, 43286, 43873, 44021, 44365, 44718, 45026, 45245,
    45465, 45682, 45887, 46049, 46235, 46495
]

async def fetch_single_satellite(norad_id: int, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    if not API_KEY or API_KEY == "DEMO_KEY":
        print(f"[KeepTrack] No API key for {norad_id}")
        return None
    url = f"{KEEPTRACK_BASE}/v4/sats/{norad_id}"
    headers = {"X-API-Key": API_KEY}
    try:
        start = time.time()
        resp = await client.get(url, headers=headers, timeout=15.0)
        latency = round((time.time() - start) * 1000, 2)
        print(f"[KeepTrack] {norad_id}: status={resp.status_code}, latency={latency}ms")
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                sat = data[0]
                sat["_api_latency_ms"] = latency
                sat["_source"] = "keeptrack"
                return sat
            elif isinstance(data, dict):
                data["_api_latency_ms"] = latency
                data["_source"] = "keeptrack"
                return data
        elif resp.status_code == 404:
            print(f"[KeepTrack] {norad_id}: Not found (404)")
        elif resp.status_code == 401:
            print(f"[KeepTrack] {norad_id}: Unauthorized (401)")
            return None
        else:
            print(f"[KeepTrack] {norad_id}: Error {resp.status_code}, body={resp.text[:100]}")
    except httpx.TimeoutException:
        print(f"[KeepTrack] {norad_id}: Timeout")
    except Exception as e:
        print(f"[KeepTrack] {norad_id}: Exception {type(e).__name__}: {e}")
    return None

async def fetch_satellites(limit: int = 30) -> List[Dict[str, Any]]:
    if not API_KEY or API_KEY == "DEMO_KEY":
        print("[KeepTrack] No API key configured")
        return []
    
    ids_to_fetch = KNOWN_SATELLITES[:limit]
    print(f"[KeepTrack] Fetching {len(ids_to_fetch)} satellites...")
    
    satellites = []
    async with httpx.AsyncClient() as client:
        # Sequential fetch with small delay to avoid rate limits
        for norad_id in ids_to_fetch:
            result = await fetch_single_satellite(norad_id, client)
            if result:
                satellites.append(result)
            await asyncio.sleep(0.1)  # 100ms delay between requests
    
    print(f"[KeepTrack] Total fetched: {len(satellites)}/{len(ids_to_fetch)}")
    return satellites

async def fetch_tle(norad_id: str) -> Optional[Dict[str, Any]]:
    if not API_KEY or API_KEY == "DEMO_KEY":
        return None
    url = f"{KEEPTRACK_BASE}/v4/sat/{norad_id}/tle"
    headers = {"X-API-Key": API_KEY}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            print(f"[KeepTrack] TLE {norad_id}: status={resp.status_code}")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"[KeepTrack] TLE {norad_id}: Exception {type(e).__name__}: {e}")
    return None
