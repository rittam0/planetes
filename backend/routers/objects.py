from fastapi import APIRouter
from services.keeptrack import fetch_satellites
from services.nasa import fetch_asteroid_feed
from services.sgp4_service import propagate_tle
from routers.metrics import record_call, record_latency, record_data_count, record_error
from datetime import datetime, timedelta
import hashlib
import math
import time
import asyncio

router = APIRouter(prefix="/api")

def _representative_position(object_id: str) -> tuple[float, float, float]:
    digest = hashlib.sha256(str(object_id).encode("utf-8")).digest()
    latitude = (int.from_bytes(digest[0:4], "big") / (2**32 - 1)) * 180 - 90
    longitude = (int.from_bytes(digest[4:8], "big") / (2**32 - 1)) * 360 - 180
    inclination = (int.from_bytes(digest[8:12], "big") / (2**32 - 1)) * 180
    return round(latitude, 2), round(longitude, 2), round(inclination, 2)

def _satellite_to_object(sat: dict) -> dict:
    tle1 = sat.get("TLE_LINE_1", "")
    tle2 = sat.get("TLE_LINE_2", "")
    propagated = None
    if tle1 and tle2 and len(tle1) > 50 and len(tle2) > 50:
        propagated = propagate_tle(tle1, tle2)
        if propagated:
            record_latency("sgp4", propagated.get("latency_ms", 0))
    
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
    
    name = sat.get("NAME") or sat.get("name") or sat.get("OBJECT_NAME") or sat.get("object_name") or "Unknown"
    norad_id = sat.get("NORAD_CAT_ID") or sat.get("norad_id") or sat.get("norad_cat_id") or "unknown"
    operator = sat.get("BUS") or sat.get("operator") or sat.get("OWNER") or sat.get("owner") or "Unknown"
    country = sat.get("COUNTRY") or sat.get("country") or sat.get("NATION") or sat.get("nation") or "Unknown"
    mass = sat.get("DRY_MASS") or sat.get("mass") or sat.get("MASS") or sat.get("dry_mass") or "Unknown"
    mission = sat.get("CONFIGURATION") or sat.get("mission") or sat.get("PURPOSE") or sat.get("purpose") or "Unknown"
    
    representative = _representative_position(str(norad_id))
    obj = {
        "norad_id": str(norad_id),
        "name": name,
        "category": "active_satellite",
        "altitude_km": int(altitude),
        "velocity_kms": velocity,
        "latitude": propagated["latitude"] if propagated else representative[0],
        "longitude": propagated["longitude"] if propagated else representative[1],
        "inclination_deg": round(inclination, 2),
        "period_min": period,
        "operator": operator,
        "country": country,
        "launch_date": "Unknown",
        "mass_kg": mass,
        "mission": mission,
        "source": "keeptrack",
        "data_status": "live",
        "position_mode": "sgp4" if propagated else "representative",
        "position_accuracy": "sgp4_derived" if propagated else "not_current_position",
        "visualization_mode": "orbital_position" if propagated else "representative",
        "source_epoch": sat.get("EPOCH") or sat.get("epoch"),
        "retrieved_at": datetime.utcnow().isoformat() + "Z",
        "api_latency_ms": sat.get("_api_latency_ms", 0),
        "sgp4_propagation": propagated
    }
    return obj

def _neo_to_object(item: dict) -> dict:
    approach = item.get("close_approach_data", [{}])[0]
    miss_km = float(approach.get("miss_distance", {}).get("kilometers", 0))
    scaled_alt = miss_km / 1000.0 if miss_km > 0 else 50000
    scaled_alt = max(15000, min(80000, scaled_alt))
    
    object_id = str(item.get("neo_reference_id") or item.get("id") or "unknown-asteroid")
    latitude, longitude, inclination = _representative_position(object_id)
    return {
        "norad_id": object_id,
        "name": item.get("name", "Unknown"),
        "category": "asteroid",
        "altitude_km": round(scaled_alt, 0),
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
        "retrieved_at": datetime.utcnow().isoformat() + "Z",
        "real_miss_distance_km": round(miss_km, 0)
    }

@router.get("/objects")
async def get_objects(limit: int = 5000, search: str = ""):
    start = time.time()
    record_call("objects")
    
    # Date range for NASA
    today = datetime.now().strftime("%Y-%m-%d")
    week_later = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    # 1. Fetch live satellites AND NASA asteroids concurrently
    sat_task = fetch_satellites(limit=min(limit, 50))
    nasa_task = fetch_asteroid_feed(today, week_later)
    
    sat_result, nasa_result = await asyncio.gather(
        sat_task, nasa_task, return_exceptions=True
    )
    
    # Handle KeepTrack result
    if isinstance(sat_result, Exception):
        print(f"[Objects] KeepTrack failed: {sat_result}")
        satellites = []
        record_error("keeptrack")
    else:
        satellites = sat_result
        for sat in satellites:
            if sat.get("_api_latency_ms"):
                record_latency("keeptrack", sat["_api_latency_ms"])
    
    # Handle NASA result
    if isinstance(nasa_result, Exception):
        print(f"[Objects] NASA failed: {nasa_result}")
        neo_data = None
        record_error("nasa")
    else:
        neo_data = nasa_result
        if neo_data and neo_data.get("_api_latency_ms"):
            record_latency("nasa", neo_data["_api_latency_ms"])
    
    # 2. Convert satellites to objects
    objects = [_satellite_to_object(sat) for sat in satellites]
    
    # 3. Merge NASA asteroids. Synthetic debris is disabled in the live endpoint.
    nasa_count = 0
    if neo_data and "near_earth_objects" in neo_data:
        for date, items in neo_data["near_earth_objects"].items():
            for item in items:
                objects.append(_neo_to_object(item))
                nasa_count += 1
    
    # 4. Apply search filter
    if search:
        objects = [o for o in objects if search.lower() in o.get("name", "").lower()]
    
    sgp4_count = sum(1 for o in objects if o.get("sgp4_propagation"))
    record_data_count("live_satellites", len(satellites))
    record_data_count("nasa_asteroids", nasa_count)
    record_data_count("synthetic_objects", 0)
    record_data_count("sgp4_propagated", sgp4_count)
    
    total_latency = round((time.time() - start) * 1000, 2)
    
    return {
        "objects": objects[:limit],
        "total": len(objects),
        "source": "keeptrack+nasa",
        "data_status": "live" if satellites or nasa_count else "degraded",
        "degraded_sources": [
            source for source, available in (
                ("keeptrack", bool(satellites)),
                ("nasa", bool(nasa_count)),
            ) if not available
        ],
        "api_latency_ms": total_latency,
        "live_satellites": len(satellites),
        "nasa_asteroids": nasa_count,
        "synthetic_objects": 0,
        "sgp4_propagated": sgp4_count
    }
