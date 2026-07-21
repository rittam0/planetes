import httpx
from config import KEEPTRACK_API_KEY, KEEPTRACK_BASE_URL

_headers = {"Authorization": f"Bearer {KEEPTRACK_API_KEY}"} if KEEPTRACK_API_KEY != "DEMO_KEY" else {}

async def fetch_catalog(limit: int = 5000):
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{KEEPTRACK_BASE_URL}/catalog",
            headers=_headers,
            params={"limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

async def fetch_satellite(norad_id: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{KEEPTRACK_BASE_URL}/sats/{norad_id}",
            headers=_headers
        )
        resp.raise_for_status()
        return resp.json()
