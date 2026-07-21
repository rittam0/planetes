from fastapi import APIRouter
from services.nasa import fetch_asteroid_feed
from datetime import datetime, timedelta
import random
import time

router = APIRouter(prefix="/api")

def _mock_asteroids():
    names = ["Apophis", "Bennu", "Ryugu", "Didymos", "Toutatis", "Eros", "Itokawa", "Ceres", "Vesta", "Pallas"]
    objs = []
    for i in range(10):
        objs.append({
            "norad_id": f"AST-{1000+i}",
            "name": f"{random.choice(names)}-{i+1}",
            "category": "asteroid",
            "altitude_km": round(random.uniform(500000, 50000000), 0),
            "velocity_kms": round(random.uniform(5, 30), 2),
            "latitude": round(random.uniform(-90, 90), 2),
            "longitude": round(random.uniform(-180, 180), 2),
            "inclination_deg": round(random.uniform(0, 180), 2),
            "period_min": 0,
            "operator": "N/A",
            "country": "N/A",
            "launch_date": "N/A",
            "mass_kg": random.choice(["1e15", "1e12", "1e9", "1e6", "1e18"]),
            "mission": "Near-Earth Object",
            "diameter_km": round(random.uniform(0.1, 50), 2),
            "hazardous": random.choice([True, False]),
            "approach_date": f"{random.randint(2024, 2030)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "source": "mock"
        })
    return objs

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
                    neos.append({
                        "norad_id": item.get("neo_reference_id", f"AST-{random.randint(1000,9999)}"),
                        "name": item.get("name", "Unknown"),
                        "category": "asteroid",
                        "altitude_km": round(miss_km, 0),
                        "velocity_kms": float(approach.get("relative_velocity", {}).get("kilometers_per_second", 0)),
                        "latitude": round(random.uniform(-90, 90), 2),
                        "longitude": round(random.uniform(-180, 180), 2),
                        "inclination_deg": round(random.uniform(0, 180), 2),
                        "period_min": 0,
                        "operator": "N/A",
                        "country": "N/A",
                        "launch_date": "N/A",
                        "mass_kg": "Unknown",
                        "mission": "Near-Earth Object",
                        "diameter_km": item.get("estimated_diameter", {}).get("kilometers", {}).get("estimated_diameter_max", 0),
                        "hazardous": item.get("is_potentially_hazardous_asteroid", False),
                        "approach_date": approach.get("close_approach_date", ""),
                        "source": "nasa"
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
    objs = _mock_asteroids()
    return {
        "objects": objs,
        "total": len(objs),
        "source": "mock",
        "api_latency_ms": round((time.time() - start) * 1000, 2),
        "warning": "NASA API unavailable. Using mock asteroid data."
    }
