from fastapi import APIRouter, Query
from services.keeptrack import (
    classify_object_type,
    configured_object_limit,
    fetch_catalogue,
    has_valid_tle,
    MAX_ORBITAL_OBJECTS,
    select_balanced_records,
)
from services.nasa import fetch_asteroid_feed
from services.sgp4_service import propagate_tle
from routers.metrics import record_call, record_latency, record_data_count, record_error
from datetime import datetime, timedelta, timezone
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

def _satellite_to_object(sat: dict, timestamp: datetime | None = None) -> dict | None:
    tle1 = sat["tle1"]
    tle2 = sat["tle2"]
    propagated = propagate_tle(tle1, tle2, timestamp)
    if not propagated:
        return None
    record_latency("sgp4", propagated.get("latency_ms", 0))

    inclination = 0.0
    eccentricity = 0.0
    mean_motion = 0.0
    try:
        inclination = float(tle2[8:16])
        eccentricity = float(f"0.{tle2[26:33].strip()}")
        mean_motion = float(tle2[52:63])
    except (TypeError, ValueError):
        return None
    period = round(1440.0 / mean_motion, 1)
    semi_major = (398600.4418 / (mean_motion * 2 * math.pi / 86400) ** 2) ** (1 / 3)
    apogee = semi_major * (1 + eccentricity) - 6371.0
    perigee = semi_major * (1 - eccentricity) - 6371.0
    velocity = math.sqrt(sum(value * value for value in propagated["velocity_kms"]))
    norad_id = propagated["norad_id"]
    obj = {
        "norad_id": str(norad_id),
        "name": sat.get("name") or sat.get("altName") or f"NORAD {norad_id}",
        "category": classify_object_type(sat),
        "tle_line1": tle1,
        "tle_line2": tle2,
        "epoch": propagated["tle_epoch"],
        "eccentricity": eccentricity,
        "mean_motion": mean_motion,
        "apogee_km": round(apogee, 2),
        "perigee_km": round(perigee, 2),
        "altitude_km": propagated["altitude_km"],
        "velocity_kms": round(velocity, 2),
        "latitude": propagated["latitude"],
        "longitude": propagated["longitude"],
        "inclination_deg": round(inclination, 2),
        "period_min": period,
        "operator": "Unknown",
        "country": sat.get("country") or "Unknown",
        "launch_date": "Unknown",
        "mass_kg": "Unknown",
        "mission": sat.get("purpose") or "Unknown",
        "source": "keeptrack",
        "data_source": "keeptrack",
        "data_status": "live",
        "position_mode": "sgp4",
        "position_accuracy": "sgp4_derived",
        "visualization_mode": "orbital_position",
        "source_epoch": propagated["tle_epoch"],
        "retrieved_at": propagated["propagated_at"],
        "updated_at": propagated["propagated_at"],
        "api_latency_ms": 0,
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
async def get_objects(
    limit: int | None = Query(default=None, ge=1, le=3000),
    search: str = "",
):
    start = time.time()
    record_call("objects")
    limit = limit or configured_object_limit()
    
    # Date range for NASA
    today = datetime.now().strftime("%Y-%m-%d")
    week_later = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    # 1. Fetch the cached orbital catalogue and NASA asteroids concurrently.
    sat_task = fetch_catalogue()
    nasa_task = fetch_asteroid_feed(today, week_later)
    
    sat_result, nasa_result = await asyncio.gather(
        sat_task, nasa_task, return_exceptions=True
    )
    
    # Handle KeepTrack result
    if isinstance(sat_result, Exception):
        print(f"[Objects] KeepTrack failed: {sat_result}")
        catalogue, cache = [], None
        record_error("keeptrack")
    else:
        catalogue, cache = sat_result
        record_latency("keeptrack", cache["latency_ms"])
    
    # Handle NASA result
    if isinstance(nasa_result, Exception):
        print(f"[Objects] NASA failed: {nasa_result}")
        neo_data = None
        record_error("nasa")
    else:
        neo_data = nasa_result
        if neo_data and neo_data.get("_api_latency_ms"):
            record_latency("nasa", neo_data["_api_latency_ms"])
    
    # 2. Select valid typed TLEs, then propagate all at one current-UTC instant.
    selected = select_balanced_records(catalogue, limit)
    reserve = select_balanced_records(
        catalogue, min(MAX_ORBITAL_OBJECTS, limit + max(20, limit // 100))
    )
    selected_ids = {id(record) for record in selected}
    selected.extend(record for record in reserve if id(record) not in selected_ids)
    propagated_at = datetime.now(timezone.utc)
    satellites = []
    rejected_count = 0
    for sat in selected:
        obj = _satellite_to_object(sat, propagated_at)
        if obj is None:
            rejected_count += 1
        else:
            satellites.append(obj)
        if len(satellites) == limit:
            break
    objects = list(satellites)
    
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
    
    sgp4_count = len(satellites)
    record_data_count("live_satellites", len(satellites))
    record_data_count("nasa_asteroids", nasa_count)
    record_data_count("synthetic_objects", 0)
    record_data_count("sgp4_propagated", sgp4_count)
    
    total_latency = round((time.time() - start) * 1000, 2)
    
    return {
        "objects": objects,
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
        "sgp4_propagated": sgp4_count,
        "catalogue": cache,
        "catalogue_record_count": len(catalogue),
        "usable_orbital_count": sum(
            1 for record in catalogue
            if classify_object_type(record) and has_valid_tle(record)
        ),
        "propagation_rejected": rejected_count,
        "active_satellites": sum(
            o["category"] == "active_satellite" for o in satellites
        ),
        "debris": sum(o["category"] == "debris" for o in satellites),
        "rocket_bodies": sum(o["category"] == "rocket_body" for o in satellites),
    }
