from fastapi import APIRouter
from services.sgp4_service import compute_conjunction_risk
import time

router = APIRouter(prefix="/api")

@router.get("/conjunctions")
async def get_conjunctions():
    start = time.time()
    satellites = [
        {"norad_id": "25544", "name": "ISS", "altitude_km": 408, "velocity_kms": 7.66, "latitude": 51.64, "longitude": -0.36, "mass_kg": 420000, "category": "active_satellite"},
        {"norad_id": "40000", "name": "Intelsat-1", "altitude_km": 35786, "velocity_kms": 3.07, "latitude": 0, "longitude": -100, "mass_kg": 5000, "category": "active_satellite"},
    ]
    debris = [
        {"norad_id": "50123", "name": "Fengyun-Debris-1", "altitude_km": 412, "velocity_kms": 7.62, "latitude": 51.0, "longitude": -0.5, "mass_kg": 5, "category": "debris"},
        {"norad_id": "50124", "name": "Iridium-Debris-2", "altitude_km": 780, "velocity_kms": 7.5, "latitude": 72.0, "longitude": 100, "mass_kg": 200, "category": "debris"},
    ]
    encounters = []
    for sat in satellites:
        for deb in debris:
            risk = compute_conjunction_risk(sat, deb)
            if risk["distance_km"] < 100:
                encounters.append({
                    "conjunction_id": f"conj-{sat['norad_id']}-{deb['norad_id']}",
                    "object_a": sat,
                    "object_b": deb,
                    "risk_analysis": risk,
                    "screening_method": "physics-informed-haversine-sgp4",
                    "timestamp": time.time()
                })
    return {
        "encounters": encounters,
        "total": len(encounters),
        "high_risk_count": sum(1 for e in encounters if e["risk_analysis"]["risk_level"] == "HIGH"),
        "screening_latency_ms": round((time.time() - start) * 1000, 2),
        "method": "all-pairs-haversine + kinetic-energy-risk-model"
    }
