"""Real SGP4 orbital propagation service.

Uses the sgp4 Python library to propagate TLEs to real positions/velocities.
Measures computation latency for metrics.
"""
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sgp4.api import Satrec, jday
import math

def propagate_tle(tle_line1: str, tle_line2: str, timestamp: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    start_time = time.time()
    
    try:
        satellite = Satrec.twoline2rv(tle_line1, tle_line2)
        
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        jd, fr = jday(timestamp.year, timestamp.month, timestamp.day, 
                      timestamp.hour, timestamp.minute, timestamp.second + timestamp.microsecond / 1e6)
        
        e, r, v = satellite.sgp4(jd, fr)
        
        if e != 0:
            return None
        
        x, y, z = r
        vx, vy, vz = v
        
        r_mag = math.sqrt(x*x + y*y + z*z)
        altitude = r_mag - 6371.0
        
        lat = math.degrees(math.asin(z / r_mag))
        lon = math.degrees(math.atan2(y, x))
        
        latency_ms = round((time.time() - start_time) * 1000, 3)
        
        return {
            "position_km": [round(x, 3), round(y, 3), round(z, 3)],
            "velocity_kms": [round(vx, 3), round(vy, 3), round(vz, 3)],
            "latitude": round(lat, 2),
            "longitude": round(lon, 2),
            "altitude_km": round(altitude, 2),
            "latency_ms": latency_ms,
            "method": "sgp4"
        }
    except Exception as e:
        print(f"[SGP4] Propagation error: {e}")
        return None

def compute_conjunction_risk(obj1: Dict[str, Any], obj2: Dict[str, Any]) -> Dict[str, Any]:
    start_time = time.time()
    
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
    
    proximity_factor = max(0, 1 - distance_km / 50)
    
    alt_avg = (alt1 + alt2) / 2
    if alt_avg < 2000:
        regime_factor = 1.0
    elif alt_avg < 35786:
        regime_factor = 0.5
    else:
        regime_factor = 0.2
    
    risk_score = min(1.0, (ke / 1e12) * proximity_factor * regime_factor)
    
    if distance_km < 1:
        probability = 1e-3
    elif distance_km < 5:
        probability = 1e-4
    elif distance_km < 10:
        probability = 1e-5
    else:
        probability = 1e-6
    
    latency_ms = round((time.time() - start_time) * 1000, 3)
    
    return {
        "distance_km": round(distance_km, 3),
        "relative_velocity_kms": round(rel_vel, 3),
        "combined_mass_kg": total_mass,
        "kinetic_energy_j": round(ke, 2),
        "risk_score": round(risk_score, 6),
        "collision_probability": probability,
        "risk_level": "HIGH" if risk_score > 0.5 else "MEDIUM" if risk_score > 0.1 else "LOW",
        "regime": "LEO" if alt_avg < 2000 else "MEO" if alt_avg < 35786 else "GEO",
        "latency_ms": latency_ms,
        "method": "physics-informed-haversine"
    }
