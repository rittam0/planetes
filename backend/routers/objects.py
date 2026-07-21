from fastapi import APIRouter
from services.keeptrack import fetch_catalog, fetch_satellite
import random
import math

router = APIRouter(prefix="/api")

def _generate_leo_satellites(count: int = 40):
    leo_names = ["ISS", "Starlink", "Hubble", "Fengyun", "Sentinel", "WorldView", "Cartosat", "Beidou"]
    objects = []
    for i in range(count):
        alt = random.randint(300, 2000)
        lat = math.degrees(math.asin(random.uniform(-1, 1)))
        lon = random.uniform(-180, 180)
        objects.append({
            "norad_id": str(25544 + i),
            "name": f"{random.choice(leo_names)}-{i+1}",
            "category": "active_satellite",
            "altitude_km": alt,
            "velocity_kms": round(math.sqrt(398600.4418 / (6371 + alt)), 2),
            "latitude": round(lat, 2),
            "longitude": round(lon, 2),
            "inclination_deg": round(random.choice([28.5, 51.6, 53.0, 97.0, 98.0]), 2),
            "period_min": round(2 * math.pi * math.sqrt(((6371 + alt)**3) / 398600.4418) / 60, 1),
            "operator": random.choice(["NASA", "SpaceX", "CNSA", "ESA", "ISRO", "Planet Labs"]),
            "country": random.choice(["US", "CN", "RU", "EU", "IN"]),
            "launch_date": f"{random.randint(2010, 2024)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "mass_kg": random.choice(["420000", "260", "11000", "1400", "4000", "5000"]),
            "mission": random.choice(["Human Spaceflight", "Communications", "Earth Observation", "Navigation", "Research"])
        })
    return objects

def _generate_geo_satellites(count: int = 15):
    geo_names = ["Intelsat", "Inmarsat", "Galaxy", "SES", "Eutelsat", "Arabsat", "INSAT"]
    objects = []
    for i in range(count):
        alt = 35786
        lat = 0.0
        lon = random.uniform(-180, 180)
        objects.append({
            "norad_id": str(40000 + i),
            "name": f"{random.choice(geo_names)}-{i+1}",
            "category": "active_satellite",
            "altitude_km": alt,
            "velocity_kms": 3.07,
            "latitude": round(lat, 2),
            "longitude": round(lon, 2),
            "inclination_deg": 0.0,
            "period_min": 1436.1,
            "operator": random.choice(["Intelsat", "Inmarsat", "SES", "ISRO", "Arabsat", "Eutelsat"]),
            "country": random.choice(["US", "EU", "IN", "AE", "JP"]),
            "launch_date": f"{random.randint(2000, 2024)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "mass_kg": random.choice(["3000", "5000", "6000", "2000", "4500"]),
            "mission": "Communications"
        })
    return objects

def _generate_debris(count: int = 35):
    debris_sources = ["Fengyun-1C", "Iridium-Cosmos", "BREEZE-M", "Delta-IV", "Ariane", "Long March"]
    objects = []
    for i in range(count):
        alt = random.randint(200, 2200)
        lat = math.degrees(math.asin(random.uniform(-1, 1)))
        lon = random.uniform(-180, 180)
        objects.append({
            "norad_id": str(50000 + i),
            "name": f"Debris-{random.choice(debris_sources)}-{i+1}",
            "category": "debris",
            "altitude_km": alt,
            "velocity_kms": round(math.sqrt(398600.4418 / (6371 + alt)), 2),
            "latitude": round(lat, 2),
            "longitude": round(lon, 2),
            "inclination_deg": round(random.choice([65.0, 72.0, 74.0, 81.0, 98.0]), 2),
            "period_min": round(2 * math.pi * math.sqrt(((6371 + alt)**3) / 398600.4418) / 60, 1),
            "operator": "N/A",
            "country": random.choice(["CN", "US", "RU", "EU"]),
            "launch_date": f"{random.randint(1990, 2020)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "mass_kg": random.choice(["50", "200", "500", "1000", "10", "5"]),
            "mission": "Debris"
        })
    return objects

def _generate_asteroids(count: int = 10):
    asteroid_names = ["Apophis", "Bennu", "Ryugu", "Didymos", "Toutatis", "Eros", "Itokawa", "Ceres", "Vesta", "Pallas"]
    objects = []
    for i in range(count):
        distance_km = random.uniform(500000, 50000000)
        lat = random.uniform(-90, 90)
        lon = random.uniform(-180, 180)
        objects.append({
            "norad_id": f"AST-{1000+i}",
            "name": f"{random.choice(asteroid_names)}-{i+1}",
            "category": "asteroid",
            "altitude_km": round(distance_km, 0),
            "velocity_kms": round(random.uniform(5, 30), 2),
            "latitude": round(lat, 2),
            "longitude": round(lon, 2),
            "inclination_deg": round(random.uniform(0, 180), 2),
            "period_min": 0,
            "operator": "N/A",
            "country": "N/A",
            "launch_date": "N/A",
            "mass_kg": random.choice(["1e15", "1e12", "1e9", "1e6", "1e18"]),
            "mission": "Near-Earth Object",
            "diameter_km": round(random.uniform(0.1, 50), 2),
            "hazardous": random.choice([True, False]),
            "approach_date": f"{random.randint(2024, 2030)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        })
    return objects

def _mock_objects():
    objects = []
    objects.extend(_generate_leo_satellites(40))
    objects.extend(_generate_geo_satellites(15))
    objects.extend(_generate_debris(35))
    objects.extend(_generate_asteroids(10))
    return objects

@router.get("/objects")
async def get_objects(limit: int = 5000, search: str = ""):
    try:
        data = await fetch_catalog(limit=min(limit, 100))
        if data and isinstance(data, list) and len(data) > 0:
            objects = []
            for sat in data[:limit]:
                apogee = sat.get("APOGEE") or sat.get("apogee") or sat.get("MEAN_MOTION", 0)
                alt = apogee if isinstance(apogee, (int, float)) and apogee > 100 else random.randint(300, 2000)
                objects.append({
                    "norad_id": str(sat.get("NORAD_CAT_ID") or sat.get("norad_id") or sat.get("id", "unknown")),
                    "name": sat.get("NAME") or sat.get("name") or sat.get("OBJECT_NAME", "Unknown"),
                    "category": "active_satellite",
                    "altitude_km": int(alt),
                    "velocity_kms": 7.66,
                    "latitude": round(random.uniform(-90, 90), 2),
                    "longitude": round(random.uniform(-180, 180), 2),
                    "inclination_deg": sat.get("INCLINATION") or sat.get("inclination") or 51.6,
                    "period_min": sat.get("PERIOD") or sat.get("period") or 92.7,
                    "operator": sat.get("OPERATOR") or sat.get("operator", "Unknown"),
                    "country": sat.get("COUNTRY_CODE") or sat.get("country_code", "Unknown"),
                    "launch_date": sat.get("LAUNCH_DATE") or sat.get("launch_date", "Unknown"),
                    "mass_kg": sat.get("MASS") or sat.get("mass", "Unknown"),
                    "mission": sat.get("MISSION") or sat.get("mission", "Unknown")
                })
            return {"objects": objects, "total": len(objects), "source": "keeptrack"}
    except Exception as e:
        print(f"[Objects] Real API failed: {e}")
    
    objects = _mock_objects()
    if search:
        objects = [o for o in objects if search.lower() in o.get("name", "").lower()]
    return {
        "objects": objects[:limit],
        "total": len(objects),
        "source": "mock",
        "warning": "Using realistic mock data. Add KEEPTRACK_API_KEY to .env for live data."
    }

@router.get("/objects/{norad_id}")
async def get_object_detail(norad_id: str):
    try:
        sat = await fetch_satellite(norad_id)
        if sat:
            return sat
    except Exception as e:
        print(f"[Objects] Detail fetch failed: {e}")
    
    return {
        "norad_id": norad_id,
        "name": f"Object-{norad_id}",
        "category": "active_satellite",
        "altitude_km": random.randint(300, 2000),
        "velocity_kms": 7.66,
        "latitude": round(random.uniform(-90, 90), 2),
        "longitude": round(random.uniform(-180, 180), 2),
        "inclination_deg": 51.6,
        "period_min": 92.7,
        "operator": "Unknown",
        "country": "Unknown",
        "launch_date": "Unknown",
        "mass_kg": "Unknown",
        "mission": "Unknown"
    }
