from agents import langgraph_graph
from agents.langgraph_graph import run_investigation, validate_numeric_facts


SATELLITE = {
    "norad_id": "25544",
    "name": "ISS",
    "category": "active_satellite",
    "source": "keeptrack",
    "data_status": "live",
    "altitude_km": 418.2,
    "velocity_kms": 7.66,
    "latitude": 10.0,
    "longitude": 20.0,
    "inclination_deg": 51.64,
    "period_min": 92.9,
    "position_mode": "sgp4",
}

ASTEROID = {
    "norad_id": "2000433",
    "name": "433 Eros",
    "category": "asteroid",
    "source": "nasa",
    "data_status": "live",
    "altitude_km": 50000,
    "velocity_kms": 12.3,
    "latitude": 1.0,
    "longitude": 2.0,
    "inclination_deg": 3.0,
    "period_min": 0,
    "approach_date": "2026-07-24",
    "real_miss_distance_km": 1234567,
    "diameter_km": 0.42,
    "hazardous": False,
    "visualization_mode": "representative_compressed",
}


def test_selected_object_reaches_langgraph_state(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = run_investigation(SATELLITE)
    assert result["normalized_object"]["norad_id"] == SATELLITE["norad_id"]
    assert result["normalized_object"]["altitude_km"] == SATELLITE["altitude_km"]


def test_satellite_route_selected(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = run_investigation(SATELLITE)
    assert result["route"] == "orbital"
    assert result["analysis"]["analysis_type"] == "satellite_debris"
    assert "No operational collision probability" in result["analysis"]["risk_statement"]


def test_asteroid_route_selected(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = run_investigation(ASTEROID)
    assert result["route"] == "asteroid"
    assert result["analysis"]["analysis_type"] == "asteroid_approach"
    assert "No impact probability" in result["analysis"]["risk_statement"]


def test_numeric_validation_matches_deterministic_fields():
    analysis = {"numeric_facts": {"altitude_km": 418.2, "velocity_kms": 7.66}}
    report = {
        "summary": "Summary",
        "interpretation": "Interpretation",
        "recommendation": "Recommendation",
        "numeric_facts": {"altitude_km": 418.2, "velocity_kms": 7.66},
    }
    assert validate_numeric_facts(report, analysis)
    report["numeric_facts"]["altitude_km"] = 999
    assert not validate_numeric_facts(report, analysis)


def test_malformed_groq_output_triggers_fallback(monkeypatch):
    monkeypatch.setattr(
        langgraph_graph,
        "generate_report",
        lambda **kwargs: {
            "status": "malformed_json",
            "report": None,
            "latency_ms": 1.0,
        },
    )
    result = run_investigation(SATELLITE)
    assert result["llm_enabled"] is False
    assert result["llm_status"] == "malformed_json"
    assert result["output_validated"] is True
    assert result["structured_report"]["numeric_facts"]["altitude_km"] == 418.2


def test_missing_groq_key_triggers_fallback(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = run_investigation(SATELLITE)
    assert result["llm_enabled"] is False
    assert result["llm_status"] == "missing_key"
    assert result["report"]


def test_unvalidated_result_never_claims_verified_sources(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    simulated = {**SATELLITE, "source": "simulated", "data_status": "simulated"}
    result = run_investigation(simulated)
    assert result["output_validated"] is True
    assert result["sources_verified"] is False
