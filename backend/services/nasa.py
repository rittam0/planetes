import httpx
from config import NASA_API_KEY, NASA_BASE_URL

async def fetch_asteroid_feed(start_date: str, end_date: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{NASA_BASE_URL}/feed",
            params={
                "start_date": start_date,
                "end_date": end_date,
                "api_key": NASA_API_KEY
            }
        )
        resp.raise_for_status()
        return resp.json()

async def fetch_asteroid_detail(asteroid_id: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{NASA_BASE_URL}/neo/{asteroid_id}",
            params={"api_key": NASA_API_KEY}
        )
        resp.raise_for_status()
        return resp.json()
