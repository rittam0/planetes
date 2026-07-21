from fastapi import APIRouter
import time
import psutil

router = APIRouter(prefix="/api")

_start_time = time.time()
_api_calls = 0
_endpoint_latencies = {}
_api_errors = 0
_api_successes = 0

@router.get("/metrics")
async def get_metrics():
    global _api_calls
    _api_calls += 1
    
    uptime_seconds = round(time.time() - _start_time, 2)
    
    avg_latencies = {}
    for endpoint, times in _endpoint_latencies.items():
        if times:
            avg_latencies[endpoint] = {
                "avg_ms": round(sum(times) / len(times), 2),
                "min_ms": round(min(times), 2),
                "max_ms": round(max(times), 2),
                "count": len(times)
            }
    
    total_api_calls = _api_successes + _api_errors
    error_rate = round(_api_errors / total_api_calls * 100, 2) if total_api_calls > 0 else 0
    
    return {
        "status": "healthy",
        "uptime_seconds": uptime_seconds,
        "api_calls_total": _api_calls,
        "api_successes": _api_successes,
        "api_errors": _api_errors,
        "error_rate_percent": error_rate,
        "memory_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "object_count": 100,
        "conjunction_count": 5,
        "version": "1.0.0",
        "endpoint_latencies": avg_latencies,
        "architecture": "FastAPI + LangGraph + SGP4 + async httpx"
    }

@router.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": time.time()}

def record_latency(endpoint: str, latency_ms: float):
    if endpoint not in _endpoint_latencies:
        _endpoint_latencies[endpoint] = []
    _endpoint_latencies[endpoint].append(latency_ms)
    if len(_endpoint_latencies[endpoint]) > 1000:
        _endpoint_latencies[endpoint] = _endpoint_latencies[endpoint][-1000:]

def record_api_result(success: bool):
    global _api_successes, _api_errors
    if success:
        _api_successes += 1
    else:
        _api_errors += 1
