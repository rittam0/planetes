from fastapi import APIRouter
from services.nasa import fetch_asteroid_feed
from datetime import datetime, timedelta

router = APIRouter(prefix="/api")

@router.get("/asteroids")
async def get_asteroids():
    today = datetime.now().strftime("%Y-%m-%d")
    week_later = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    try:
        data = await fetch_asteroid_feed(today, week_later)
        neos = []
        for date, items in data.get("near_earth_objects", {}).items():
            for item in items:
                approach = item.get("close_approach_data", [{}])[0]
                neos.append({
                    "norad_id": item.get("neo_reference_id", "unknown"),
                    "name": item.get("name", "Unknown"),
                    "category": "asteroid",
                    "altitude_km": float(approach.get("miss_distance", {}).get("kilometers", 0)),
                    "velocity_kms": float(approach.get("relative_velocity", {}).get("kilometers_per_second", 0)),
                    "diameter_km": item.get("estimated_diameter", {}).get("kilometers", {}).get("estimated_diameter_max", 0),
                    "hazardous": item.get("is_potentially_hazardous_asteroid", False),
                    "approach_date": approach.get("close_approach_date", "")
                })
        return {"objects": neos, "total": len(neos)}
    except Exception as e:
        return {"objects": [], "total": 0, "warning": f"NASA API unavailable: {str(e)}"}
