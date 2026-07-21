import os
import httpx
import asyncio
from typing import Optional, List, Dict, Any
import time

KEEPTRACK_BASE = "https://api.keeptrack.space"
API_KEY = os.getenv("KEEPTRACK_API_KEY", "DEMO_KEY")

KNOWN_SATELLITES = [
    25544, 20580, 48274, 46826, 46827, 46828, 46829, 46830,
    25560, 25994, 27453, 28654, 33591, 43013, 41308, 41942,
    43178, 43286, 43873, 44021, 44365, 44718, 45026, 45245,
    45465, 45682, 45887, 46049, 46235, 46495, 46666, 46831
]

async def fetch_single_satellite(norad_id: int, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    if not API_KEY or API_KEY == "DEMO_KEY":
        return None
    url = f"{KEEPTRACK_BASE}/v4/sats/{norad_id}"
    headers = {"X-API-Key": API_KEY}
    try:
        start = time.time()
        resp = await client.get(url, headers=headers, timeout=10.0)
        latency = round((time.time() - start) * 1000, 2)
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
            print(f"[KeepTrack] {norad_id} not found")
        elif resp.status_code == 401:
            print(f"[KeepTrack] 401 - API key invalid")
            return None
        else:
            print(f"[KeepTrack] {norad_id} error {resp.status_code}")
    except Exception as e:
        print(f"[KeepTrack] {norad_id} exception: {e}")
    return None

async def fetch_satellites(limit: int = 30) -> List[Dict[str, Any]]:
    if not API_KEY or API_KEY == "DEMO_KEY":
        return []
    ids_to_fetch = KNOWN_SATELLITES[:limit]
    async with httpx.AsyncClient() as client:
        tasks = [fetch_single_satellite(norad_id, client) for norad_id in ids_to_fetch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    satellites = []
    for result in results:
        if isinstance(result, dict) and result:
            satellites.append(result)
    print(f"[KeepTrack] Fetched {len(satellites)}/{len(ids_to_fetch)} satellites")
    return satellites

async def fetch_tle(norad_id: str) -> Optional[Dict[str, Any]]:
    if not API_KEY or API_KEY == "DEMO_KEY":
        return None
    url = f"{KEEPTRACK_BASE}/v4/sat/{norad_id}/tle"
    headers = {"X-API-Key": API_KEY}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"[KeepTrack] TLE fetch error: {e}")
    return None
