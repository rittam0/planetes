"""Pydantic models for AstraScope."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class OrbitalObject(BaseModel):
    """A satellite, debris piece, or rocket body."""
    norad_id: str = Field(..., description="NORAD catalog ID")
    name: str
    category: str = Field(..., description="active_satellite | debris | rocket_body")
    tle_line1: str
    tle_line2: str
    epoch: datetime
    inclination_deg: float
    eccentricity: float
    mean_motion: float  # revs per day
    period_min: float
    apogee_km: float
    perigee_km: float
    altitude_km: float = Field(..., description="Current propagated altitude")
    velocity_kms: float = Field(..., description="Current propagated velocity")
    latitude: float = Field(..., description="Current propagated latitude")
    longitude: float = Field(..., description="Current propagated longitude")
    data_source: str = "celestrak"
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class ConjunctionEvent(BaseModel):
    """A close-approach event from SOCRATES."""
    id: str
    primary_norad: str
    primary_name: str
    secondary_norad: str
    secondary_name: str
    tca: datetime = Field(..., description="Time of closest approach")
    max_probability: float = Field(..., description="Maximum collision probability")
    min_range_km: float = Field(..., description="Minimum miss distance in km")
    relative_velocity_kms: float
    data_source: str = "celestrak_socrates"
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class ObjectDetailResponse(BaseModel):
    """Full object detail for frontend."""
    object: OrbitalObject
    conjunctions: List[ConjunctionEvent] = []
    history_count: int = 0


class InvestigationRequest(BaseModel):
    """Request an AI investigation of a conjunction."""
    conjunction_id: str


class InvestigationResponse(BaseModel):
    """AI-generated investigation report."""
    conjunction_id: str
    report: str
    sources_verified: bool
    generated_at: datetime
    latency_ms: float


class HealthCheck(BaseModel):
    status: str
    objects_count: int
    conjunctions_count: int
    last_ingestion: Optional[datetime]
