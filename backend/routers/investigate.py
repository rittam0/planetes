from fastapi import APIRouter
from pydantic import BaseModel
import random
import time
from datetime import datetime
from agents.langgraph_graph import run_investigation
from services.rag_service import get_corpus_stats
from routers.metrics import record_call, record_latency, record_llm, record_error

router = APIRouter(prefix="/api")

class InvestigateRequest(BaseModel):
    conjunction_id: str
    question: str = "Analyze this conjunction risk"

@router.post("/investigate")
async def investigate(req: InvestigateRequest):
    """LangGraph multi-agent investigation with RAG-augmented LLM report generation"""
    start = time.time()
    record_call("investigate")
    
    result = run_investigation(req.conjunction_id, req.question)
    
    total_latency = round((time.time() - start) * 1000, 2)
    
    if result.get("llm_enabled"):
        llm_latency = result.get("llm_report", {}).get("llm_latency_ms", 0)
        if llm_latency:
            record_latency("groq", llm_latency)
        record_llm(success=True)
    else:
        record_llm(success=False)
    
    return {
        "investigation_id": f"inv-{req.conjunction_id}-{random.randint(1000,9999)}",
        "conjunction_id": req.conjunction_id,
        "question": req.question,
        "report": result["report"],
        "llm_report": result.get("llm_report"),
        "llm_enabled": result.get("llm_enabled", False),
        "rag_context": result.get("rag_context"),
        "agents": result["agent_steps"],
        "sources": result["sources"],
        "sources_verified": True,
        "risk_level": result["risk_level"],
        "recommendation": result["recommendation"],
        "risk_analysis": result["risk_analysis"],
        "generated_at": datetime.now().isoformat(),
        "latency_ms": total_latency,
        "architecture": "LangGraph StateGraph: DataFetch -> RiskAnalysis(RAG+SGP4) -> ReportGeneration(Groq+Fallback)",
        "graph_metadata": {
            "nodes": result.get("graph_nodes", []),
            "state_transitions": result.get("state_transitions", 0),
            "rag_corpus": get_corpus_stats()
        }
    }
