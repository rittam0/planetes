from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api")

class InvestigateRequest(BaseModel):
    conjunction_id: str
    question: str = "Analyze this conjunction risk"

@router.post("/investigate")
async def investigate(req: InvestigateRequest):
    return {
        "investigation_id": f"inv-{req.conjunction_id}",
        "conjunction_id": req.conjunction_id,
        "report": "LangGraph multi-agent analysis will be implemented here. Agents: Data Fetcher, Risk Analyst, Report Generator.",
        "sources_verified": False,
        "generated_at": "2024-07-21T00:00:00Z",
        "latency_ms": 0
    }
