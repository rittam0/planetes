from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from agents.langgraph_graph import run_investigation
from routers.metrics import record_call, record_latency, record_llm

router = APIRouter(prefix="/api")


class SelectedObject(BaseModel):
    model_config = ConfigDict(extra="allow")

    norad_id: str
    name: str
    category: str
    source: str
    altitude_km: Optional[float] = None
    velocity_kms: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    inclination_deg: Optional[float] = None
    period_min: Optional[float] = None
    approach_date: Optional[str] = None
    real_miss_distance_km: Optional[float] = None
    diameter_km: Optional[float] = None
    hazardous: Optional[bool] = None
    visualization_mode: Optional[str] = None
    position_accuracy: Optional[str] = None
    position_mode: Optional[str] = None
    source_epoch: Optional[str] = None
    retrieved_at: Optional[str] = None
    data_status: Optional[str] = None


class InvestigateRequest(BaseModel):
    selected_object: SelectedObject


@router.post("/investigate")
async def investigate(req: InvestigateRequest):
    """Run a stateful investigation workflow over the supplied selected object."""
    record_call("investigate")
    result = run_investigation(req.selected_object.model_dump())

    if result.get("llm_enabled"):
        latency = result.get("llm_latency_ms")
        if latency is not None:
            record_latency("groq", latency)
        record_llm(success=True)
    else:
        record_llm(success=False)

    return {
        "investigation_id": f"inv-{uuid4().hex[:12]}",
        "object_id": req.selected_object.norad_id,
        "report": result["report"],
        "structured_report": result["structured_report"],
        "analysis_type": result["analysis"]["analysis_type"],
        "llm_enabled": result["llm_enabled"],
        "llm_status": result["llm_status"],
        "llm_latency_ms": result.get("llm_latency_ms"),
        "workflow_steps": result["workflow_steps"],
        "sources": result["sources"],
        "sources_verified": result["sources_verified"],
        "source_validation": "supplied_metadata_only",
        "output_validated": result["output_validated"],
        "recommendation": result["recommendation"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "architecture": "LangGraph stateful investigation workflow",
    }
