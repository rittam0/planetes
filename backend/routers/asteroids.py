from fastapi import APIRouter
from services.nasa import fetch_asteroid_feed
from routers.metrics import record_error
from datetime import datetime, timedelta
import hashlib
import time

router = APIRouter(prefix="/api")

def _representative_position(object_id: str) -> tuple[float, float, float]:
    digest = hashlib.sha256(object_id.encode("utf-8")).digest()
    latitude = (int.from_bytes(digest[0:4], "big") / (2**32 - 1)) * 180 - 90
    longitude = (int.from_bytes(digest[4:8], "big") / (2**32 - 1)) * 360 - 180
    inclination = (int.from_bytes(digest[8:12], "big") / (2**32 - 1)) * 180
    return round(latitude, 2), round(longitude, 2), round(inclination, 2)

@router.get("/asteroids")
async def get_asteroids():
    start = time.time()
    today = datetime.now().strftime("%Y-%m-%d")
    week_later = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    try:
        data = await fetch_asteroid_feed(today, week_later)
        if data and "near_earth_objects" in data:
            neos = []
            for date, items in data["near_earth_objects"].items():
                for item in items:
                    approach = item.get("close_approach_data", [{}])[0]
                    miss_km = float(approach.get("miss_distance", {}).get("kilometers", 0))
                    object_id = str(item.get("neo_reference_id") or item.get("id") or "unknown-asteroid")
                    latitude, longitude, inclination = _representative_position(object_id)
                    neos.append({
                        "norad_id": object_id,
                        "name": item.get("name", "Unknown"),
                        "category": "asteroid",
                        "altitude_km": round(miss_km, 0),
                        "velocity_kms": float(approach.get("relative_velocity", {}).get("kilometers_per_second", 0)),
                        "latitude": latitude,
                        "longitude": longitude,
                        "inclination_deg": inclination,
                        "period_min": 0,
                        "operator": "N/A",
                        "country": "N/A",
                        "launch_date": "N/A",
                        "mass_kg": "Unknown",
                        "mission": "Near-Earth Object",
                        "diameter_km": item.get("estimated_diameter", {}).get("kilometers", {}).get("estimated_diameter_max", 0),
                        "hazardous": item.get("is_potentially_hazardous_asteroid", False),
                        "approach_date": approach.get("close_approach_date", ""),
                        "source": "nasa",
                        "data_status": "live",
                        "visualization_mode": "representative_compressed",
                        "position_accuracy": "not_ephemeris",
                        "position_mode": "representative",
                        "real_miss_distance_km": round(miss_km, 0),
                        "retrieved_at": datetime.utcnow().isoformat() + "Z",
                    })
            api_latency = data.get("_api_latency_ms", 0)
            total_latency = round((time.time() - start) * 1000, 2)
            return {
                "objects": neos,
                "total": len(neos),
                "source": "nasa",
                "api_latency_ms": total_latency,
                "nasa_api_latency_ms": api_latency,
                "date_range": f"{today} to {week_later}"
            }
    except Exception as e:
        print(f"[Asteroids] API failed: {e}")
    record_error("nasa")
    return {
        "objects": [],
        "total": 0,
        "source": "nasa",
        "data_status": "degraded",
        "degraded_data": True,
        "api_latency_ms": round((time.time() - start) * 1000, 2),
        "warning": "NASA API unavailable; no asteroid events are being reported."
    }
