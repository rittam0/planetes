"""CelesTrak data ingestion with SGP4 propagation."""
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any
from sgp4.api import Satrec, jday
import numpy as np

from backend.db.database import SessionLocal, OrbitalObjectDB, ConjunctionEventDB, IngestionLogDB

CELESTRAK_GP_URL = "https://celestrak.org/NORAD/elements/gp.php"
SOCRATES_DIR_URL = "https://celestrak.org/SOCRATES/jsonDir.php"

# Groups to fetch
default_groups = [
    "starlink", "gps-ops", "visual", "active", "stations",
    "debris", "rocket-bodies", "iridium", "orbcomm", "globalstar"
]


def fetch_group(group: str) -> List[Dict[str, Any]]:
    """Fetch orbital data for a CelesTrak group."""
    url = f"{CELESTRAK_GP_URL}?GROUP={group}&FORMAT=JSON"
    resp = httpx.get(url, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    # Handle both list and dict with "member" key
    if isinstance(data, dict) and "member" in data:
        return data["member"]
    return data if isinstance(data, list) else []


def propagate_position(satrec: Satrec, jd: float, fr: float) -> Dict[str, float]:
    """Propagate satellite to given Julian date. Returns lat/lon/alt/vel."""
    e, r, v = satrec.sgp4(jd, fr)
    if e != 0:
        return {"latitude": 0.0, "longitude": 0.0, "altitude_km": 0.0, "velocity_kms": 0.0}

    # r is position vector in km (TEME)
    # v is velocity vector in km/s (TEME)
    x, y, z = r
    vx, vy, vz = v

    # Approximate geodetic conversion (simplified)
    r_mag = np.sqrt(x*x + y*y + z*z)
    lat = np.degrees(np.arcsin(z / r_mag))
    lon = np.degrees(np.arctan2(y, x))
    alt = r_mag - 6371.0  # Earth radius ~6371 km
    vel = np.sqrt(vx*vx + vy*vy + vz*vz)

    return {
        "latitude": float(lat),
        "longitude": float(lon),
        "altitude_km": float(alt),
        "velocity_kms": float(vel)
    }


def parse_gp_to_object(record: Dict[str, Any], category: str) -> OrbitalObjectDB:
    """Convert CelesTrak GP record to DB model with propagation."""
    # Build TLE from OMM fields
    line1 = record.get("TLE_LINE1", "")
    line2 = record.get("TLE_LINE2", "")

    # If no TLE lines, construct from OMM
    if not line1 or not line2:
        satrec = Satrec()
        # Simplified: use mean motion directly
        # In production, you'd construct proper TLE
        line1 = f"1 {record.get('NORAD_CAT_ID', '00000')}U          {record.get('EPOCH', '00000.00000000')}  .00000000  00000-0  00000-0 0  9999"
        line2 = f"2 {record.get('NORAD_CAT_ID', '00000')} {record.get('MEAN_MOTION', 0):.8f} {record.get('ECCENTRICITY', 0):.8f} {record.get('INCLINATION', 0):.4f} {record.get('RA_OF_ASC_NODE', 0):.4f} {record.get('ARG_OF_PERICENTER', 0):.4f} {record.get('MEAN_ANOMALY', 0):.4f} {record.get('REV_AT_EPOCH', 0):.4f}"

    satrec = Satrec.twoline2rv(line1, line2)

    # Propagate to now
    now = datetime.now(timezone.utc)
    jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond / 1e6)
    pos = propagate_position(satrec, jd, fr)

    # Calculate period from mean motion
    mean_motion = float(record.get("MEAN_MOTION", 0))
    period_min = 1440.0 / mean_motion if mean_motion > 0 else 0.0

    # Apogee/perigee from mean motion and eccentricity
    ecc = float(record.get("ECCENTRICITY", 0))
    # Simplified: assume circular-ish orbit for altitude estimate
    semi_major = (8681663.653 / (mean_motion ** (2/3))) if mean_motion > 0 else 0
    apogee = (semi_major * (1 + ecc) - 6371.0) / 1000.0 if semi_major > 0 else 0
    perigee = (semi_major * (1 - ecc) - 6371.0) / 1000.0 if semi_major > 0 else 0

    return OrbitalObjectDB(
        norad_id=str(record.get("NORAD_CAT_ID", "")),
        name=record.get("OBJECT_NAME", "Unknown"),
        category=category,
        tle_line1=line1,
        tle_line2=line2,
        epoch=datetime.strptime(record.get("EPOCH", "2000-001T00:00:00.000"), "%Y-%jT%H:%M:%S.%f").replace(tzinfo=timezone.utc),
        inclination_deg=float(record.get("INCLINATION", 0)),
        eccentricity=ecc,
        mean_motion=mean_motion,
        period_min=period_min,
        apogee_km=apogee,
        perigee_km=perigee,
        altitude_km=pos["altitude_km"],
        velocity_kms=pos["velocity_kms"],
        latitude=pos["latitude"],
        longitude=pos["longitude"],
        data_source="celestrak",
        updated_at=datetime.utcnow()
    )


def ingest_celestrak_groups(groups: List[str] = None) -> Dict[str, int]:
    """Ingest orbital data from CelesTrak. Returns counts."""
    groups = groups or default_groups
    db = SessionLocal()
    log = IngestionLogDB(source="celestrak_gp", status="running")
    db.add(log)
    db.commit()

    total = 0
    errors = []

    try:
        for group in groups:
            try:
                records = fetch_group(group)
                # Map group name to category
                category_map = {
                    "debris": "debris",
                    "rocket-bodies": "rocket_body",
                }
                category = category_map.get(group, "active_satellite")

                for record in records:
                    try:
                        obj = parse_gp_to_object(record, category)
                        # Upsert
                        existing = db.query(OrbitalObjectDB).filter_by(norad_id=obj.norad_id).first()
                        if existing:
                            for key, value in obj.__dict__.items():
                                if not key.startswith("_"):
                                    setattr(existing, key, value)
                        else:
                            db.add(obj)
                        total += 1
                    except Exception as e:
                        errors.append(f"{group}/{record.get('NORAD_CAT_ID', '?')}: {str(e)}")

                db.commit()
            except Exception as e:
                errors.append(f"{group}: {str(e)}")

        log.status = "success" if not errors else "partial"
        log.objects_ingested = total
        log.error_message = "; ".join(errors[:10]) if errors else None
        log.completed_at = datetime.utcnow()
        db.commit()

        return {"total": total, "errors": len(errors), "status": log.status}

    except Exception as e:
        log.status = "failure"
        log.error_message = str(e)
        log.completed_at = datetime.utcnow()
        db.commit()
        return {"total": total, "errors": len(errors) + 1, "status": "failure"}

    finally:
        db.close()


def fetch_socrates() -> List[Dict[str, Any]]:
    """Fetch SOCRATES conjunction data."""
    try:
        resp = httpx.get(SOCRATES_DIR_URL, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        # Parse directory to find latest data file
        if isinstance(data, list):
            # Find most recent entry
            latest = max(data, key=lambda x: x.get("date", ""))
            file_url = latest.get("url", "")
            if file_url:
                resp2 = httpx.get(file_url, timeout=30.0)
                resp2.raise_for_status()
                return resp2.json() if resp2.headers.get("content-type", "").startswith("application/json") else []
        return []
    except Exception:
        return []


def ingest_socrates() -> Dict[str, int]:
    """Ingest SOCRATES conjunction events."""
    db = SessionLocal()
    log = IngestionLogDB(source="celestrak_socrates", status="running")
    db.add(log)
    db.commit()

    try:
        events = fetch_socrates()
        total = 0

        for event in events:
            try:
                ev = ConjunctionEventDB(
                    id=f"{event.get('PRIMARY', '')}_{event.get('SECONDARY', '')}_{event.get('TCA', '')}",
                    primary_norad=str(event.get("PRIMARY", "")),
                    primary_name=event.get("PRIMARY_NAME", "Unknown"),
                    secondary_norad=str(event.get("SECONDARY", "")),
                    secondary_name=event.get("SECONDARY_NAME", "Unknown"),
                    tca=datetime.fromisoformat(event.get("TCA", "2000-01-01T00:00:00").replace("Z", "+00:00")),
                    max_probability=float(event.get("MAX_PROB", 0) or 0),
                    min_range_km=float(event.get("MIN_RANGE", 0) or 0),
                    relative_velocity_kms=float(event.get("REL_VEL", 0) or 0),
                    updated_at=datetime.utcnow()
                )
                db.merge(ev)
                total += 1
            except Exception:
                continue

        db.commit()
        log.status = "success"
        log.objects_ingested = total
        log.completed_at = datetime.utcnow()
        db.commit()

        return {"total": total, "status": "success"}

    except Exception as e:
        log.status = "failure"
        log.error_message = str(e)
        log.completed_at = datetime.utcnow()
        db.commit()
        return {"total": 0, "status": "failure"}

    finally:
        db.close()
