from fastapi import APIRouter
from services.keeptrack import fetch_satellites
from services.nasa import fetch_asteroid_feed
from services.sgp4_service import propagate_tle
from datetime import datetime, timedelta
import random
import math
import time

router = APIRouter(prefix="/api")

def _generate_debris(count=35):
    sources = ["Fengyun-1C", "Iridium-Cosmos", "BREEZE-M", "Delta-IV", "Ariane", "Long March"]
    objs = []
    for i in range(count):
        alt = random.randint(200, 2200)
        objs.append({
            "norad_id": str(50000 + i),
            "name": f"Debris-{random.choice(sources)}-{i+1}",
            "category": "debris",
            "altitude_km": alt,
            "velocity_kms": round(math.sqrt(398600.4418 / (6371 + alt)), 2),
            "latitude": round(math.degrees(math.asin(random.uniform(-1, 1))), 2),
            "longitude": round(random.uniform(-180, 180), 2),
            "inclination_deg": round(random.choice([65.0, 72.0, 74.0, 81.0, 98.0]), 2),
            "period_min": round(2 * math.pi * math.sqrt(((6371 + alt)**3) / 398600.4418) / 60, 1),
            "operator": "N/A",
            "country": random.choice(["CN", "US", "RU", "EU"]),
            "launch_date": f"{random.randint(1990, 2020)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "mass_kg": random.choice(["50", "200", "500", "1000"]),
            "mission": "Debris",
            "source": "mock"
        })
    return objs

def _satellite_to_object(sat: dict) -> dict:
    tle1 = sat.get("TLE_LINE_1", "")
    tle2 = sat.get("TLE_LINE_2", "")
    propagated = None
    if tle1 and tle2 and len(tle1) > 50 and len(tle2) > 50:
        propagated = propagate_tle(tle1, tle2)
    inclination = 51.6
    try:
        if tle2 and len(tle2) > 80:
            inclination = float(tle2[8:16].strip())
    except:
        pass
    period = 92.7
    try:
        if tle2 and len(tle2) > 63:
            mean_motion = float(tle2[52:63].strip())
            if mean_motion > 0:
                period = round(1440.0 / mean_motion, 1)
    except:
        pass
    altitude = 400
    if propagated:
        altitude = propagated["altitude_km"]
    else:
        try:
            if tle2 and len(tle2) > 63:
                mean_motion = float(tle2[52:63].strip())
                if mean_motion > 0:
                    sma = (398600.4418 / (mean_motion * 2 * math.pi / 86400) ** 2) ** (1/3)
                    altitude = round(sma - 6371, 0)
        except:
            pass
    velocity = 7.66
    if altitude > 100:
        velocity = round(math.sqrt(398600.4418 / (6371 + altitude)), 2)
    obj = {
        "norad_id": str(sat.get("NORAD_CAT_ID", sat.get("norad_id", "unknown"))),
        "name": sat.get("NAME", sat.get("name", "Unknown")),
        "category": "active_satellite",
        "altitude_km": int(altitude),
        "velocity_kms": velocity,
        "latitude": propagated["latitude"] if propagated else round(random.uniform(-90, 90), 2),
        "longitude": propagated["longitude"] if propagated else round(random.uniform(-180, 180), 2),
        "inclination_deg": round(inclination, 2),
        "period_min": period,
        "operator": sat.get("BUS", sat.get("operator", "Unknown")),
        "country": sat.get("COUNTRY", sat.get("country", "Unknown")),
        "launch_date": "Unknown",
        "mass_kg": sat.get("DRY_MASS", sat.get("mass", "Unknown")),
        "mission": sat.get("CONFIGURATION", sat.get("mission", "Unknown")),
        "source": "keeptrack",
        "api_latency_ms": sat.get("_api_latency_ms", 0),
        "sgp4_propagation": propagated
    }
    return obj

def _neo_to_object(item: dict) -> dict:
    """Convert NASA NEO to frontend-compatible object with scaled distance."""
    approach = item.get("close_approach_data", [{}])[0]
    miss_km = float(approach.get("miss_distance", {}).get("kilometers", 0))
    
    # Scale asteroid distance so it appears in the 3D scene
    # Real miss distances are 15M-70M km — way off screen
    # Scale: divide by 1000 → 15,000-70,000 km, visible as distant ring
    scaled_alt = miss_km / 1000.0 if miss_km > 0 else 50000
    
    # Clamp to reasonable visible range (15k - 80k km from Earth center)
    scaled_alt = max(15000, min(80000, scaled_alt))
    
    return {
        "norad_id": item.get("neo_reference_id", f"AST-{random.randint(1000,9999)}"),
        "name": item.get("name", "Unknown"),
        "category": "asteroid",
        "altitude_km": round(scaled_alt, 0),
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
        "source": "nasa",
        "real_miss_distance_km": round(miss_km, 0)  # preserve real value for detail panel
    }

@router.get("/objects")
async def get_objects(limit: int = 5000, search: str = ""):
    start = time.time()
    
    # 1. Fetch live satellites from KeepTrack
    satellites = await fetch_satellites(limit=min(limit, 30))
    objects = [_satellite_to_object(sat) for sat in satellites]
    
    # 2. Generate debris
    debris = _generate_debris(35)
    objects.extend(debris)
    
    # 3. Fetch NASA asteroids and merge
    nasa_count = 0
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        week_later = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        neo_data = await fetch_asteroid_feed(today, week_later)
        if neo_data and "near_earth_objects" in neo_data:
            for date, items in neo_data["near_earth_objects"].items():
                for item in items:
                    objects.append(_neo_to_object(item))
                    nasa_count += 1
    except Exception as e:
        print(f"[Objects] NASA fetch failed: {e}")
    
    # 4. Apply search filter
    if search:
        objects = [o for o in objects if search.lower() in o.get("name", "").lower()]
    
    total_latency = round((time.time() - start) * 1000, 2)
    
    return {
        "objects": objects[:limit],
        "total": len(objects),
        "source": "keeptrack+nasa+mock",
        "api_latency_ms": total_latency,
        "live_satellites": len(satellites),
        "nasa_asteroids": nasa_count,
        "mock_debris": len(debris),
        "sgp4_propagated": sum(1 for o in objects if o.get("sgp4_propagation"))
    }
