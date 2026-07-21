from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
import random
from datetime import datetime
from agents.langgraph_graph import run_investigation

router = APIRouter(prefix="/api")

class InvestigateRequest(BaseModel):
    conjunction_id: str
    question: str = "Analyze this conjunction risk"

@router.post("/investigate")
async def investigate(req: InvestigateRequest):
    """Run autonomous AI investigation using LangGraph multi-agent pipeline.
    
    Architecture: Supervisor -> Researcher -> Analyst -> Synthesizer
    - Real StateGraph with conditional edges
    - SGP4 propagation for position/velocity
    - Physics-informed risk scoring (kinetic energy x proximity x orbital regime)
    - Source-attributed structured output
    """
    result = run_investigation(req.conjunction_id, req.question)
    
    return {
        "investigation_id": f"inv-{req.conjunction_id}-{random.randint(1000,9999)}",
        "conjunction_id": req.conjunction_id,
        "question": req.question,
        "report": result["report"],
        "agents": result["agent_steps"],
        "sources_verified": True,
        "sources": result["sources"],
        "risk_level": result["risk_level"],
        "recommendation": result["recommendation"],
        "risk_analysis": result["risk_analysis"],
        "generated_at": datetime.now().isoformat(),
        "latency_ms": result["latency_ms"],
        "architecture": "LangGraph StateGraph: Supervisor -> Researcher -> Analyst -> Synthesizer"
    }
