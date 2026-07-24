import asyncio
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

KEEPTRACK_CATALOGUE_URL = "https://api.keeptrack.space/v4/sats/brief"
API_KEY = os.getenv("KEEPTRACK_API_KEY", "DEMO_KEY")
CATALOGUE_TTL_SECONDS = int(os.getenv("KEEPTRACK_CACHE_TTL_SECONDS", "86400"))
MAX_ORBITAL_OBJECTS = 3000

_catalogue_cache: Dict[str, Any] = {
    "records": [],
    "fetched_at": None,
    "expires_at": None,
    "source": "keeptrack_v4_sats_brief",
    "etag": None,
}
_cache_lock = asyncio.Lock()


def configured_object_limit() -> int:
    requested = int(os.getenv("ORBITAL_OBJECT_LIMIT", "2000"))
    return max(1, min(requested, MAX_ORBITAL_OBJECTS))


def clear_catalogue_cache() -> None:
    _catalogue_cache.update({
        "records": [],
        "fetched_at": None,
        "expires_at": None,
        "source": "keeptrack_v4_sats_brief",
        "etag": None,
    })


def _cache_metadata(*, stale: bool, cache_hit: bool, latency_ms: float) -> Dict[str, Any]:
    return {
        "fetched_at": (
            _catalogue_cache["fetched_at"].isoformat()
            if _catalogue_cache["fetched_at"] else None
        ),
        "expires_at": (
            _catalogue_cache["expires_at"].isoformat()
            if _catalogue_cache["expires_at"] else None
        ),
        "record_count": len(_catalogue_cache["records"]),
        "source": _catalogue_cache["source"],
        "stale": stale,
        "cache_hit": cache_hit,
        "latency_ms": round(latency_ms, 2),
        "etag": _catalogue_cache["etag"],
    }


async def _fetch_upstream_catalogue() -> tuple[List[Dict[str, Any]], Dict[str, str]]:
    if not API_KEY or API_KEY == "DEMO_KEY":
        raise RuntimeError("KEEPTRACK_API_KEY is not configured")
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.get(
            KEEPTRACK_CATALOGUE_URL,
            headers={"X-API-Key": API_KEY, "Accept": "application/json"},
        )
        response.raise_for_status()
        records = response.json()
        if not isinstance(records, list):
            raise ValueError("KeepTrack catalogue response is not a JSON array")
        headers = {
            "etag": response.headers.get("etag", ""),
            "data_updated_at": response.headers.get("x-data-updated-at", ""),
        }
        return records, headers


async def fetch_catalogue(force_refresh: bool = False) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    start = time.perf_counter()
    now = datetime.now(timezone.utc)
    if (
        not force_refresh
        and _catalogue_cache["records"]
        and _catalogue_cache["expires_at"]
        and now < _catalogue_cache["expires_at"]
    ):
        return _catalogue_cache["records"], _cache_metadata(
            stale=False,
            cache_hit=True,
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    async with _cache_lock:
        now = datetime.now(timezone.utc)
        if (
            not force_refresh
            and _catalogue_cache["records"]
            and _catalogue_cache["expires_at"]
            and now < _catalogue_cache["expires_at"]
        ):
            return _catalogue_cache["records"], _cache_metadata(
                stale=False,
                cache_hit=True,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        try:
            records, headers = await _fetch_upstream_catalogue()
            fetched_at = datetime.now(timezone.utc)
            _catalogue_cache.update({
                "records": records,
                "fetched_at": fetched_at,
                "expires_at": fetched_at + timedelta(seconds=CATALOGUE_TTL_SECONDS),
                "source": "keeptrack_v4_sats_brief",
                "etag": headers.get("etag") or None,
            })
            return records, _cache_metadata(
                stale=False,
                cache_hit=False,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as exc:
            if _catalogue_cache["records"]:
                metadata = _cache_metadata(
                    stale=True,
                    cache_hit=True,
                    latency_ms=(time.perf_counter() - start) * 1000,
                )
                metadata["refresh_error"] = f"{type(exc).__name__}: {exc}"
                return _catalogue_cache["records"], metadata
            raise


def classify_object_type(record: Dict[str, Any]) -> Optional[str]:
    object_type = record.get("type")
    if object_type == 1:
        return "active_satellite"
    if object_type == 2:
        return "rocket_body"
    if object_type == 3:
        return "debris"
    return None


def has_valid_tle(record: Dict[str, Any]) -> bool:
    line1 = record.get("tle1")
    line2 = record.get("tle2")
    return (
        isinstance(line1, str)
        and isinstance(line2, str)
        and line1.startswith("1 ")
        and line2.startswith("2 ")
        and len(line1) >= 60
        and len(line2) >= 60
    )


def select_balanced_records(
    records: List[Dict[str, Any]], limit: int
) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, MAX_ORBITAL_OBJECTS))
    buckets = {
        "active_satellite": [],
        "debris": [],
        "rocket_body": [],
    }
    for record in records:
        category = classify_object_type(record)
        if category and has_valid_tle(record):
            buckets[category].append(record)

    quotas = {
        "active_satellite": round(limit * 0.4),
        "debris": round(limit * 0.4),
    }
    quotas["rocket_body"] = limit - sum(quotas.values())
    selected: List[Dict[str, Any]] = []
    leftovers: List[Dict[str, Any]] = []
    for category in ("active_satellite", "debris", "rocket_body"):
        bucket = buckets[category]
        selected.extend(bucket[:quotas[category]])
        leftovers.extend(bucket[quotas[category]:])
    if len(selected) < limit:
        selected.extend(leftovers[:limit - len(selected)])
    return selected[:limit]
