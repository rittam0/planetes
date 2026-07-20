"""AstraScope — FastAPI backend."""
import os
import time
import json
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.db.database import init_db, get_db, get_cached, set_cached, OrbitalObjectDB, ConjunctionEventDB, IngestionLogDB
from backend.ingestion.celestrak import ingest_celestrak_groups, ingest_socrates
from backend.agents.workflow import run_investigation
from backend.models.schemas import (
    OrbitalObject, ConjunctionEvent, ObjectDetailResponse,
    InvestigationRequest, InvestigationResponse, HealthCheck
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB and run initial ingestion."""
    init_db()
    # Initial ingestion (non-blocking, runs in background)
    import threading
    def _ingest():
        ingest_celestrak_groups()
        ingest_socrates()
    threading.Thread(target=_ingest, daemon=True).start()
    yield
    # Shutdown cleanup if needed


app = FastAPI(
    title="AstraScope API",
    description="Autonomous Space Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthCheck)
def health_check(db: Session = Depends(get_db)):
    """Health check with counts."""
    objects_count = db.query(OrbitalObjectDB).count()
    conjunctions_count = db.query(ConjunctionEventDB).count()
    last_ingestion = db.query(IngestionLogDB).order_by(IngestionLogDB.completed_at.desc()).first()

    return HealthCheck(
        status="healthy",
        objects_count=objects_count,
        conjunctions_count=conjunctions_count,
        last_ingestion=last_ingestion.completed_at if last_ingestion else None
    )


@app.get("/api/objects")
def list_objects(
    category: str = Query(None, description="Filter by category: active_satellite, debris, rocket_body"),
    search: str = Query(None, description="Search by name or NORAD ID"),
    limit: int = Query(100, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List orbital objects with optional filtering."""
    start = time.time()

    # Cache key
    cache_key = f"objects:{category}:{search}:{limit}:{offset}"
    cached = get_cached(cache_key, ttl=300)
    if cached:
        return json.loads(cached)

    query = db.query(OrbitalObjectDB)

    if category:
        query = query.filter(OrbitalObjectDB.category == category)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (OrbitalObjectDB.name.ilike(search_filter)) |
            (OrbitalObjectDB.norad_id.ilike(search_filter))
        )

    total = query.count()
    objects = query.offset(offset).limit(limit).all()

    result = {
        "total": total,
        "limit": limit,
        "offset": offset,
        "objects": [
            {
                "norad_id": o.norad_id,
                "name": o.name,
                "category": o.category,
                "altitude_km": round(o.altitude_km, 1),
                "velocity_kms": round(o.velocity_kms, 2),
                "latitude": round(o.latitude, 2),
                "longitude": round(o.longitude, 2),
                "inclination_deg": round(o.inclination_deg, 2),
                "period_min": round(o.period_min, 1)
            }
            for o in objects
        ],
        "latency_ms": round((time.time() - start) * 1000, 1)
    }

    set_cached(cache_key, json.dumps(result), ttl=300)
    return result


@app.get("/api/objects/{norad_id}", response_model=ObjectDetailResponse)
def get_object_detail(norad_id: str, db: Session = Depends(get_db)):
    """Get full details for a single object including conjunctions."""
    start = time.time()

    cache_key = f"object:{norad_id}"
    cached = get_cached(cache_key, ttl=600)
    if cached:
        return ObjectDetailResponse.parse_raw(cached)

    obj = db.query(OrbitalObjectDB).filter_by(norad_id=norad_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Object {norad_id} not found")

    conjunctions = db.query(ConjunctionEventDB).filter_by(primary_norad=norad_id).all()

    result = ObjectDetailResponse(
        object=OrbitalObject.from_orm(obj),
        conjunctions=[ConjunctionEvent.from_orm(c) for c in conjunctions],
        history_count=0
    )

    set_cached(cache_key, result.json(), ttl=600)
    return result


@app.get("/api/conjunctions")
def list_conjunctions(
    min_probability: float = Query(0.0, ge=0.0),
    max_range_km: float = Query(None, ge=0.0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List upcoming conjunction events."""
    start = time.time()

    query = db.query(ConjunctionEventDB).filter(ConjunctionEventDB.max_probability >= min_probability)
    if max_range_km:
        query = query.filter(ConjunctionEventDB.min_range_km <= max_range_km)

    events = query.order_by(ConjunctionEventDB.tca).limit(limit).all()

    return {
        "total": len(events),
        "conjunctions": [
            {
                "id": e.id,
                "primary_norad": e.primary_norad,
                "primary_name": e.primary_name,
                "secondary_norad": e.secondary_norad,
                "secondary_name": e.secondary_name,
                "tca": e.tca.isoformat(),
                "max_probability": e.max_probability,
                "min_range_km": e.min_range_km,
                "relative_velocity_kms": e.relative_velocity_kms
            }
            for e in events
        ],
        "latency_ms": round((time.time() - start) * 1000, 1)
    }


@app.post("/api/investigate", response_model=InvestigationResponse)
def investigate(request: InvestigationRequest):
    """Run an AI investigation on a conjunction event."""
    # Find the conjunction
    from backend.db.database import SessionLocal
    db = SessionLocal()
    try:
        event = db.query(ConjunctionEventDB).filter_by(id=request.conjunction_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Conjunction not found")

        query = (
            f"Investigate the conjunction between {event.primary_name} "
            f"(NORAD: {event.primary_norad}) and {event.secondary_name} "
            f"(NORAD: {event.secondary_norad}). "
            f"Time of closest approach: {event.tca.isoformat()}. "
            f"Miss distance: {event.min_range_km:.3f} km. "
            f"Max collision probability: {event.max_probability:.2e}. "
            f"Relative velocity: {event.relative_velocity_kms:.2f} km/s. "
            f"Explain the risk level and what this means for space operations."
        )

        result = run_investigation(query, investigation_id=request.conjunction_id)

        return InvestigationResponse(
            conjunction_id=request.conjunction_id,
            report=result["response"],
            sources_verified=True,
            generated_at=datetime.utcnow(),
            latency_ms=result["latency_ms"]
        )
    finally:
        db.close()


@app.post("/api/ingest/trigger")
def trigger_ingestion():
    """Manually trigger data ingestion."""
    result1 = ingest_celestrak_groups()
    result2 = ingest_socrates()
    return {
        "celestrak": result1,
        "socrates": result2,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
