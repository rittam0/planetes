import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sgp4.api import Satrec, jday
import math

def propagate_tle(tle_line1: str, tle_line2: str, timestamp=None):
    start = time.time()
    try:
        satellite = Satrec.twoline2rv(tle_line1, tle_line2)
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        jd, fr = jday(timestamp.year, timestamp.month, timestamp.day,
                      timestamp.hour, timestamp.minute, timestamp.second)
        e, r, v = satellite.sgp4(jd, fr)
        if e != 0:
            return None
        x, y, z = r
        vx, vy, vz = v
        r_mag = math.sqrt(x*x + y*y + z*z)
        altitude = r_mag - 6371.0
        lat = math.degrees(math.asin(z / r_mag))
        lon = math.degrees(math.atan2(y, x))
        return {
            "position_km": [round(x, 2), round(y, 2), round(z, 2)],
            "velocity_kms": [round(vx, 2), round(vy, 2), round(vz, 2)],
            "latitude": round(lat, 2),
            "longitude": round(lon, 2),
            "altitude_km": round(altitude, 2),
            "latency_ms": round((time.time() - start) * 1000, 3),
            "method": "sgp4"
        }
    except Exception as e:
        print(f"[SGP4] Error: {e}")
        return None

def compute_conjunction_risk(obj1, obj2):
    start = time.time()
    alt1 = obj1.get("altitude_km", 400)
    alt2 = obj2.get("altitude_km", 400)
    vel1 = obj1.get("velocity_kms", 7.66)
    vel2 = obj2.get("velocity_kms", 7.66)
    lat1 = math.radians(obj1.get("latitude", 0))
    lon1 = math.radians(obj1.get("longitude", 0))
    lat2 = math.radians(obj2.get("latitude", 0))
    lon2 = math.radians(obj2.get("longitude", 0))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    distance_km = c * (6371 + (alt1 + alt2) / 2)
    rel_vel = abs(vel1 - vel2)
    mass1 = float(obj1.get("mass_kg", 5000)) if obj1.get("mass_kg") not in [None, "Unknown", "N/A"] else 5000
    mass2 = float(obj2.get("mass_kg", 100)) if obj2.get("mass_kg") not in [None, "Unknown", "N/A"] else 100
    total_mass = mass1 + mass2
    ke = 0.5 * total_mass * (rel_vel * 1000) ** 2
    proximity = max(0, 1 - distance_km / 50)
    alt_avg = (alt1 + alt2) / 2
    regime = 1.0 if alt_avg < 2000 else 0.5 if alt_avg < 35786 else 0.2
    risk_score = min(1.0, (ke / 1e12) * proximity * regime)
    if distance_km < 1: prob = 1e-3
    elif distance_km < 5: prob = 1e-4
    elif distance_km < 10: prob = 1e-5
    else: prob = 1e-6
    return {
        "distance_km": round(distance_km, 2),
        "relative_velocity_kms": round(rel_vel, 2),
        "combined_mass_kg": total_mass,
        "kinetic_energy_j": round(ke, 2),
        "risk_score": round(risk_score, 6),
        "collision_probability": prob,
        "risk_level": "HIGH" if risk_score > 0.5 else "MEDIUM" if risk_score > 0.1 else "LOW",
        "regime": "LEO" if alt_avg < 2000 else "MEO" if alt_avg < 35786 else "GEO",
        "latency_ms": round((time.time() - start) * 1000, 2),
        "method": "physics-informed-haversine"
    }
