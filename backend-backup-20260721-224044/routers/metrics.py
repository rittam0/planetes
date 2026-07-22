from fastapi import APIRouter
import time
import psutil

router = APIRouter(prefix="/api")

_start_time = time.time()
_api_calls = 0

@router.get("/metrics")
async def get_metrics():
    global _api_calls
    _api_calls += 1
    return {
        "status": "healthy",
        "uptime_seconds": round(time.time() - _start_time, 2),
        "api_calls_total": _api_calls,
        "memory_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "version": "1.0.0",
        "architecture": "FastAPI + SGP4 + async httpx + real API integration",
        "live_apis": ["keeptrack", "nasa", "groq"],
        "features": [
            "Real-time SGP4 orbital propagation",
            "Physics-informed conjunction risk scoring",
            "Live KeepTrack satellite catalog",
            "Live NASA NeoWs asteroid tracking",
            "Groq LLM structured report generation",
            "Deterministic fallback for 100% uptime"
        ]
    }

@router.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": time.time()}
