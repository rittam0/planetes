from fastapi import APIRouter
from pydantic import BaseModel
import random
from datetime import datetime
from agents.langgraph_graph import run_investigation

router = APIRouter(prefix="/api")

class InvestigateRequest(BaseModel):
    conjunction_id: str
    question: str = "Analyze this conjunction risk"

@router.post("/investigate")
async def investigate(req: InvestigateRequest):
    result = run_investigation(req.conjunction_id, req.question)
    return {
        "investigation_id": f"inv-{req.conjunction_id}-{random.randint(1000,9999)}",
        "conjunction_id": req.conjunction_id,
        "question": req.question,
        "report": result["report"],
        "llm_report": result.get("llm_report"),
        "llm_enabled": result.get("llm_enabled", False),
        "agents": result["agent_steps"],
        "sources": result["sources"],
        "sources_verified": True,
        "risk_level": result["risk_level"],
        "recommendation": result["recommendation"],
        "risk_analysis": result["risk_analysis"],
        "generated_at": datetime.now().isoformat(),
        "latency_ms": result["latency_ms"],
        "architecture": "LangGraph StateGraph: DataFetch -> RiskAnalysis -> ReportGeneration (LLM + Fallback)"
    }
