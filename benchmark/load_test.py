import httpx
import time
import statistics
import concurrent.futures

BASE_URL = "http://localhost:8000"

def benchmark_endpoint(path, requests=100, concurrency=10):
    latencies = []
    errors = 0

    def make_request(_):
        nonlocal errors
        start = time.time()
        try:
            resp = httpx.get(f"{BASE_URL}{path}", timeout=30)
            if resp.status_code == 200:
                latencies.append((time.time() - start) * 1000)
            else:
                errors += 1
        except Exception:
            errors += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        list(executor.map(make_request, range(requests)))

    return {
        "requests": requests,
        "successful": len(latencies),
        "errors": errors,
        "p50": statistics.median(latencies) if latencies else 0,
        "p95": sorted(latencies)[int(len(latencies)*0.95)] if latencies else 0,
        "mean": statistics.mean(latencies) if latencies else 0,
        "min": min(latencies) if latencies else 0,
        "max": max(latencies) if latencies else 0,
    }

if __name__ == "__main__":
    print("=" * 60)
    print("PLANETES BENCHMARK")
    print("=" * 60)

    print("\n[1] /api/objects?limit=100")
    r1 = benchmark_endpoint("/api/objects?limit=100", requests=500, concurrency=20)
    print(f"  p50: {r1['p50']:.1f}ms | p95: {r1['p95']:.1f}ms | mean: {r1['mean']:.1f}ms")
    print(f"  errors: {r1['errors']}/{r1['requests']}")

    print("\n[2] /api/objects?limit=1000")
    r2 = benchmark_endpoint("/api/objects?limit=1000", requests=200, concurrency=10)
    print(f"  p50: {r2['p50']:.1f}ms | p95: {r2['p95']:.1f}ms | mean: {r2['mean']:.1f}ms")
    print(f"  errors: {r2['errors']}/{r2['requests']}")

    print("\n[3] /api/conjunctions")
    r3 = benchmark_endpoint("/api/conjunctions?limit=50", requests=300, concurrency=15)
    print(f"  p50: {r3['p50']:.1f}ms | p95: {r3['p95']:.1f}ms | mean: {r3['mean']:.1f}ms")
    print(f"  errors: {r3['errors']}/{r3['requests']}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Objects endpoint p95: {r1['p95']:.1f}ms")
    print(f"Conjunctions endpoint p95: {r3['p95']:.1f}ms")
    print(f"Total errors: {r1['errors'] + r2['errors'] + r3['errors']}")
