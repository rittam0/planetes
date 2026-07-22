from fastapi import APIRouter
import time
import psutil
import os
from datetime import datetime

router = APIRouter(prefix="/api")

_start_time = time.time()

_metrics = {
    "api_calls": {"total": 0, "objects": 0, "asteroids": 0, "conjunctions": 0, "investigate": 0, "metrics": 0, "health": 0},
    "latency_ms": {"keeptrack_avg": 0, "keeptrack_total": 0, "keeptrack_count": 0, "nasa_avg": 0, "nasa_total": 0, "nasa_count": 0, "groq_avg": 0, "groq_total": 0, "groq_count": 0, "sgp4_avg": 0, "sgp4_total": 0, "sgp4_count": 0},
    "data_counts": {"live_satellites": 0, "nasa_asteroids": 0, "mock_debris": 0, "sgp4_propagated": 0, "llm_success": 0, "llm_fallback": 0},
    "errors": {"keeptrack_failures": 0, "nasa_failures": 0, "groq_failures": 0}
}

def record_call(endpoint: str):
    _metrics["api_calls"]["total"] += 1
    _metrics["api_calls"][endpoint] = _metrics["api_calls"].get(endpoint, 0) + 1

def record_latency(api: str, latency_ms: float):
    m = _metrics["latency_ms"]
    m[f"{api}_total"] += latency_ms
    m[f"{api}_count"] += 1
    m[f"{api}_avg"] = round(m[f"{api}_total"] / m[f"{api}_count"], 2)

def record_data_count(key: str, count: int):
    _metrics["data_counts"][key] = count

def record_error(api: str):
    _metrics["errors"][f"{api}_failures"] += 1

def record_llm(success: bool):
    if success:
        _metrics["data_counts"]["llm_success"] += 1
    else:
        _metrics["data_counts"]["llm_fallback"] += 1

@router.get("/metrics")
async def get_metrics():
    record_call("metrics")
    uptime = time.time() - _start_time
    process = psutil.Process()
    kt_avg = _metrics["latency_ms"]["keeptrack_avg"]
    nasa_avg = _metrics["latency_ms"]["nasa_avg"]
    groq_avg = _metrics["latency_ms"]["groq_avg"]
    sgp4_avg = _metrics["latency_ms"]["sgp4_avg"]
    llm_total = _metrics["data_counts"]["llm_success"] + _metrics["data_counts"]["llm_fallback"]
    llm_rate = round(_metrics["data_counts"]["llm_success"] / llm_total * 100, 1) if llm_total > 0 else 0
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": round(uptime, 2),
        "uptime_formatted": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s",
        "api_calls": _metrics["api_calls"],
        "external_apis": {
            "keeptrack": {"status": "connected" if _metrics["data_counts"]["live_satellites"] > 0 else "degraded", "avg_latency_ms": kt_avg, "calls": _metrics["latency_ms"]["keeptrack_count"], "failures": _metrics["errors"]["keeptrack_failures"], "live_satellites": _metrics["data_counts"]["live_satellites"]},
            "nasa": {"status": "connected" if _metrics["data_counts"]["nasa_asteroids"] > 0 else "degraded", "avg_latency_ms": nasa_avg, "calls": _metrics["latency_ms"]["nasa_count"], "failures": _metrics["errors"]["nasa_failures"], "asteroids_this_week": _metrics["data_counts"]["nasa_asteroids"]},
            "groq": {"status": "connected" if _metrics["data_counts"]["llm_success"] > 0 else "degraded", "avg_latency_ms": groq_avg, "calls": _metrics["latency_ms"]["groq_count"], "failures": _metrics["errors"]["groq_failures"], "llm_success_rate_pct": llm_rate, "llm_success_count": _metrics["data_counts"]["llm_success"], "llm_fallback_count": _metrics["data_counts"]["llm_fallback"]}
        },
        "processing": {"sgp4_propagation": {"avg_latency_ms": sgp4_avg, "calls": _metrics["latency_ms"]["sgp4_count"], "propagated_objects": _metrics["data_counts"]["sgp4_propagated"]}},
        "system": {"memory_mb": round(process.memory_info().rss / 1024 / 1024, 2), "cpu_percent": psutil.cpu_percent(interval=0.1), "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"},
        "version": "1.0.0",
        "architecture": "FastAPI + SGP4 + async httpx + NASA NeoWs + KeepTrack + Groq LLM + LangGraph + RAG",
        "features": ["Real-time SGP4 orbital propagation", "Physics-informed conjunction risk scoring", "Live KeepTrack satellite catalog (30 satellites)", "Live NASA NeoWs asteroid tracking (40+ NEOs/week)", "LangGraph multi-agent AI investigation pipeline", "RAG-augmented Groq LLM structured report generation", "Deterministic fallback for 100% uptime", "Per-endpoint latency tracking", "AI layer observability"]
    }

@router.get("/health")
async def health_check():
    record_call("health")
    return {"status": "ok", "timestamp": datetime.now().isoformat(), "live_satellites": _metrics["data_counts"]["live_satellites"], "nasa_asteroids": _metrics["data_counts"]["nasa_asteroids"]}
