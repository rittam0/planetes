from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from services.groq_llm import generate_report


GENERAL_INTERPRETATION_RULES = (
    "Interpret only supplied measurements. Distinguish measured or propagated data "
    "from representative visualization coordinates. Do not infer collision or impact "
    "probability without an appropriate trajectory and uncertainty model."
)


class InvestigationState(TypedDict, total=False):
    selected_object: Dict[str, Any]
    normalized_object: Dict[str, Any]
    route: str
    analysis: Dict[str, Any]
    structured_report: Dict[str, Any]
    report: str
    recommendation: str
    workflow_steps: List[Dict[str, Any]]
    sources: List[str]
    sources_verified: bool
    output_validated: bool
    llm_enabled: bool
    llm_status: str
    llm_latency_ms: Optional[float]


def validate_and_normalize_node(state: InvestigationState) -> InvestigationState:
    supplied = dict(state["selected_object"])
    category = str(supplied.get("category") or "unknown").lower()
    supplied["category"] = category
    supplied["source"] = str(supplied.get("source") or "unknown")
    state["normalized_object"] = supplied
    state["workflow_steps"] = [{
        "step": "validate_and_normalize",
        "status": "complete",
        "detail": f"Validated supplied {category} object {supplied.get('norad_id', 'unknown')}.",
    }]
    state["sources"] = [supplied["source"]] if supplied["source"] != "unknown" else []
    return state


def route_by_category_node(state: InvestigationState) -> InvestigationState:
    category = state["normalized_object"]["category"]
    state["route"] = "asteroid" if category == "asteroid" else "orbital"
    state["workflow_steps"].append({
        "step": "route_by_category",
        "status": "complete",
        "detail": f"Selected {state['route']} analysis branch.",
    })
    return state


def route_category(state: InvestigationState) -> str:
    return state["route"]


def orbital_analysis_node(state: InvestigationState) -> InvestigationState:
    obj = state["normalized_object"]
    position_mode = obj.get("position_mode", "unavailable")
    is_propagated = position_mode == "sgp4"
    summary = (
        f"{obj.get('name', 'Unknown object')} is a {obj.get('category', 'orbital object')} "
        f"at {obj.get('altitude_km', 'unknown')} km altitude with supplied velocity "
        f"{obj.get('velocity_kms', 'unknown')} km/s, inclination "
        f"{obj.get('inclination_deg', 'unknown')}°, and period "
        f"{obj.get('period_min', 'unknown')} minutes."
    )
    provenance = (
        "The displayed position is derived from SGP4 propagation of a retrieved TLE."
        if is_propagated else
        "The displayed position is representative and is not an SGP4-derived current position."
    )
    state["analysis"] = {
        "analysis_type": "satellite_debris",
        "summary": summary,
        "provenance": provenance,
        "risk_statement": (
            "No operational collision probability is available: this object record does "
            "not include a conjunction event, covariance, or time of closest approach."
        ),
        "numeric_facts": {
            key: obj.get(key) for key in (
                "altitude_km", "velocity_kms", "inclination_deg", "period_min"
            ) if obj.get(key) is not None
        },
    }
    state["workflow_steps"].append({
        "step": "orbital_analysis",
        "status": "complete",
        "detail": "Interpreted supplied orbital fields without calculating collision probability.",
    })
    return state


def asteroid_analysis_node(state: InvestigationState) -> InvestigationState:
    obj = state["normalized_object"]
    summary = (
        f"{obj.get('name', 'Unknown asteroid')} has a NASA NeoWs approach event dated "
        f"{obj.get('approach_date') or 'unknown'}, with supplied miss distance "
        f"{obj.get('real_miss_distance_km', 'unknown')} km, relative velocity "
        f"{obj.get('velocity_kms', 'unknown')} km/s, estimated maximum diameter "
        f"{obj.get('diameter_km', 'unknown')} km, and hazardous flag "
        f"{obj.get('hazardous', 'unknown')}."
    )
    state["analysis"] = {
        "analysis_type": "asteroid_approach",
        "summary": summary,
        "provenance": (
            "Approach statistics are supplied from NASA NeoWs. Spatial placement is a "
            "representative compressed visualization, not an ephemeris."
        ),
        "risk_statement": (
            "The potentially hazardous classification is a screening flag, not an impact "
            "prediction. No impact probability is inferred."
        ),
        "numeric_facts": {
            key: obj.get(key) for key in (
                "real_miss_distance_km", "velocity_kms", "diameter_km"
            ) if obj.get(key) is not None
        },
    }
    state["workflow_steps"].append({
        "step": "asteroid_analysis",
        "status": "complete",
        "detail": "Interpreted supplied NASA approach-event fields without inventing impact probability.",
    })
    return state


def _fallback_report(state: InvestigationState) -> Dict[str, Any]:
    analysis = state["analysis"]
    return {
        "summary": analysis["summary"],
        "interpretation": f"{analysis['provenance']} {analysis['risk_statement']}",
        "recommendation": "Use this as an educational screening summary; consult authoritative orbital data for operational decisions.",
        "numeric_facts": analysis["numeric_facts"],
    }


def structured_report_node(state: InvestigationState) -> InvestigationState:
    fallback = _fallback_report(state)
    llm_result = generate_report(
        selected_object=state["normalized_object"],
        deterministic_analysis=state["analysis"],
        system_instruction=GENERAL_INTERPRETATION_RULES,
    )
    state["llm_enabled"] = llm_result["status"] == "success"
    state["llm_status"] = llm_result["status"]
    state["llm_latency_ms"] = llm_result.get("latency_ms")
    state["structured_report"] = llm_result.get("report") or fallback
    state["workflow_steps"].append({
        "step": "structured_report",
        "status": llm_result["status"],
        "detail": (
            "Generated and parsed a structured AI report."
            if state["llm_enabled"] else
            f"Used deterministic fallback ({llm_result['status']})."
        ),
    })
    return state


def validate_numeric_facts(
    report: Dict[str, Any], deterministic_analysis: Dict[str, Any]
) -> bool:
    required = {"summary", "interpretation", "recommendation", "numeric_facts"}
    if not required.issubset(report) or not isinstance(report["numeric_facts"], dict):
        return False
    expected = deterministic_analysis["numeric_facts"]
    facts = report["numeric_facts"]
    if set(facts) != set(expected):
        return False
    for key, value in expected.items():
        if key not in facts:
            return False
        try:
            if abs(float(facts[key]) - float(value)) > 1e-6:
                return False
        except (TypeError, ValueError):
            if facts[key] != value:
                return False
    return all(isinstance(report[key], str) and report[key].strip() for key in required - {"numeric_facts"})


def validate_output_node(state: InvestigationState) -> InvestigationState:
    valid = validate_numeric_facts(state["structured_report"], state["analysis"])
    if not valid:
        state["structured_report"] = _fallback_report(state)
        state["llm_enabled"] = False
        state["llm_status"] = "schema_failure"
    state["output_validated"] = validate_numeric_facts(
        state["structured_report"], state["analysis"]
    )
    # The API validates report structure and numbers, but does not re-fetch a
    # client-supplied object; source provenance therefore remains unverified.
    state["sources_verified"] = False
    report = state["structured_report"]
    state["report"] = (
        f"{report['summary']}\n\n{report['interpretation']}\n\n"
        f"Recommendation: {report['recommendation']}"
    )
    state["recommendation"] = report["recommendation"]
    state["workflow_steps"].append({
        "step": "validate_output",
        "status": "complete" if state["output_validated"] else "failed",
        "detail": "Validated required fields and deterministic numeric values.",
    })
    return state


builder = StateGraph(InvestigationState)
builder.add_node("validate_and_normalize", validate_and_normalize_node)
builder.add_node("route_by_category", route_by_category_node)
builder.add_node("orbital_analysis", orbital_analysis_node)
builder.add_node("asteroid_analysis", asteroid_analysis_node)
builder.add_node("generate_structured_report", structured_report_node)
builder.add_node("validate_output", validate_output_node)
builder.set_entry_point("validate_and_normalize")
builder.add_edge("validate_and_normalize", "route_by_category")
builder.add_conditional_edges(
    "route_by_category",
    route_category,
    {"orbital": "orbital_analysis", "asteroid": "asteroid_analysis"},
)
builder.add_edge("orbital_analysis", "generate_structured_report")
builder.add_edge("asteroid_analysis", "generate_structured_report")
builder.add_edge("generate_structured_report", "validate_output")
builder.add_edge("validate_output", END)
investigation_graph = builder.compile()


def run_investigation(selected_object: Dict[str, Any]) -> InvestigationState:
    return investigation_graph.invoke({"selected_object": selected_object})
