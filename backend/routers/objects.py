from fastapi import APIRouter, HTTPException
from services.keeptrack import fetch_catalog, fetch_satellite
import random

router = APIRouter(prefix="/api")

@router.get("/objects")
async def get_objects(limit: int = 5000, search: str = ""):
    try:
        data = await fetch_catalog(limit=limit)
        objects = data.get("data", [])
        if search:
            objects = [o for o in objects if search.lower() in o.get("NAME", "").lower()]
        return {
            "objects": objects[:limit],
            "total": len(objects)
        }
    except Exception as e:
        return {
            "objects": _mock_objects()[:limit],
            "total": len(_mock_objects()),
            "warning": f"Live data unavailable: {str(e)}"
        }

@router.get("/objects/{norad_id}")
async def get_object_detail(norad_id: str):
    try:
        sat = await fetch_satellite(norad_id)
        return sat
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Satellite not found: {str(e)}")

def _mock_objects():
    categories = ["active_satellite", "debris", "asteroid"]
    names = ["ISS", "Hubble", "Starlink-1", "Debris-A", "Asteroid-2024", "GPS-IIR", "Fengyun-1C"]
    objects = []
    for i in range(100):
        cat = random.choice(categories)
        alt = random.randint(200, 36000)
        objects.append({
            "norad_id": str(25544 + i),
            "name": f"{random.choice(names)}-{i}",
            "category": cat,
            "altitude_km": alt,
            "velocity_kms": round(7.5 + random.random() * 0.5, 2),
            "latitude": round(random.uniform(-90, 90), 2),
            "longitude": round(random.uniform(-180, 180), 2),
            "inclination_deg": round(random.uniform(0, 98), 2),
            "period_min": round(90 + random.random() * 30, 1)
        })
    return objects
