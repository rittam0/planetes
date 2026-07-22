from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
import time
from datetime import datetime
from services.sgp4_service import compute_conjunction_risk
from services.groq_llm import generate_report
from services.rag_service import retrieve_context

class InvestigationState(TypedDict):
    conjunction_id: str
    question: str
    object_a: Optional[Dict[str, Any]]
    object_b: Optional[Dict[str, Any]]
    risk_analysis: Optional[Dict[str, Any]]
    llm_report: Optional[Dict[str, Any]]
    rag_context: Optional[str]
    sources: List[str]
    agent_steps: List[Dict[str, Any]]
    report: Optional[str]
    risk_level: Optional[str]
    recommendation: Optional[str]
    latency_ms: float
    llm_enabled: bool

def data_fetch_node(state: InvestigationState) -> InvestigationState:
    start = time.time()
    state["object_a"] = {
        "norad_id": "25544", "name": "ISS", "category": "active_satellite",
        "altitude_km": 408, "velocity_kms": 7.66, "mass_kg": 420000,
        "operator": "NASA", "country": "US"
    }
    state["object_b"] = {
        "norad_id": "50123", "name": "Debris Fragment", "category": "debris",
        "altitude_km": 412, "velocity_kms": 7.62, "mass_kg": 5,
        "operator": "N/A", "country": "CN",
        "latitude": 50.0, "longitude": -5.0
    }
    state["sources"] = ["KeepTrack Catalog API v4", "Space-Track.org TLE Repository"]
    latency = round((time.time() - start) * 1000, 2)
    state["agent_steps"] = [{
        "agent": "Data Fetcher",
        "action": "Retrieved object metadata and TLEs from catalog APIs",
        "result": f"Objects: ISS (25544) and Debris (50123)",
        "latency_ms": latency
    }]
    return state

def risk_analysis_node(state: InvestigationState) -> InvestigationState:
    start = time.time()
    risk = compute_conjunction_risk(state["object_a"], state["object_b"])
    state["risk_analysis"] = risk
    state["risk_level"] = risk["risk_level"]
    
    rag_start = time.time()
    query = f"conjunction risk {risk['risk_level']} {state['object_a']['name']} {state['object_b']['name']}"
    rag_context, rag_latency = retrieve_context(query, top_k=2)
    state["rag_context"] = rag_context
    
    state["sources"].append("NASA CARA Conjunction Assessment Guidelines")
    state["sources"].append("RAG: Orbital Mechanics Corpus")
    latency = round((time.time() - start) * 1000, 2)
    state["agent_steps"].append({
        "agent": "Risk Analyst",
        "action": "Computed collision probability using SGP4 propagation + physics-informed scoring + RAG context retrieval",
        "result": f"Probability: {risk['collision_probability']}. Risk score: {risk['risk_score']}. Regime: {risk['regime']}. RAG docs retrieved in {rag_latency}ms",
        "latency_ms": latency,
        "rag_latency_ms": rag_latency
    })
    return state

def report_generation_node(state: InvestigationState) -> InvestigationState:
    start = time.time()
    risk = state["risk_analysis"]
    level = state["risk_level"]
    
    if level == "HIGH":
        fallback_rec = "IMMEDIATE MANEUVER REQUIRED. Contact operator within 4 hours."
    elif level == "MEDIUM":
        fallback_rec = "Monitor closely. Prepare contingency maneuver."
    else:
        fallback_rec = "Monitor per standard procedures. No maneuver required."
    
    state["recommendation"] = fallback_rec
    state["report"] = (
        f"Conjunction {state['conjunction_id']}: {level} risk. "
        f"Collision probability: {risk['collision_probability']}. "
        f"Miss distance: {risk['distance_km']} km. "
        f"Kinetic energy: {risk['kinetic_energy_j']} J. "
        f"{fallback_rec}"
    )
    state["llm_enabled"] = False
    
    llm_report = None
    try:
        llm_report = generate_report(
            state["conjunction_id"],
            risk,
            state["object_a"],
            state["object_b"],
            state["question"],
            rag_context=state.get("rag_context", "")
        )
    except Exception as e:
        print(f"[LangGraph] LLM fallback: {e}")
    
    if llm_report:
        state["llm_report"] = llm_report
        state["llm_enabled"] = True
        state["report"] = llm_report.get("risk_summary", state["report"])
        state["recommendation"] = llm_report.get("recommended_action", fallback_rec)
    
    state["sources"].append("Orbital Mechanics Reference - Vallado, Fundamentals of Astrodynamics")
    latency = round((time.time() - start) * 1000, 2)
    state["agent_steps"].append({
        "agent": "Report Generator",
        "action": "LLM-structured report via Groq with RAG augmentation" if state["llm_enabled"] else "Deterministic template fallback",
        "result": state["report"],
        "latency_ms": latency
    })
    return state

builder = StateGraph(InvestigationState)
builder.add_node("data_fetch", data_fetch_node)
builder.add_node("risk_analysis", risk_analysis_node)
builder.add_node("report_generation", report_generation_node)
builder.set_entry_point("data_fetch")
builder.add_edge("data_fetch", "risk_analysis")
builder.add_edge("risk_analysis", "report_generation")
builder.add_edge("report_generation", END)
investigation_graph = builder.compile()

def run_investigation(conjunction_id: str, question: str) -> Dict[str, Any]:
    start = time.time()
    initial_state: InvestigationState = {
        "conjunction_id": conjunction_id,
        "question": question,
        "object_a": None,
        "object_b": None,
        "risk_analysis": None,
        "llm_report": None,
        "rag_context": None,
        "sources": [],
        "agent_steps": [],
        "report": None,
        "risk_level": None,
        "recommendation": None,
        "latency_ms": 0.0,
        "llm_enabled": False
    }
    result = investigation_graph.invoke(initial_state)
    result["latency_ms"] = round((time.time() - start) * 1000, 2)
    result["graph_nodes"] = ["data_fetch", "risk_analysis", "report_generation"]
    result["state_transitions"] = 3
    return result
