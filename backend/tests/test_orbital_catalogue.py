from datetime import datetime, timedelta, timezone

import httpx
import pytest

from models.schemas import OrbitalObject
from services import keeptrack
from services.sgp4_service import propagate_tle


TLES = {
    1: (
        "Vanguard 1",
        "1 00005U 58002B   26204.05730786  .00000276  00000+0  34013-3 0  9998",
        "2 00005  34.2507 203.6367 1836871 300.2143  42.9032 10.86019063447180",
    ),
    2: (
        "VANGUARD R/B",
        "1 00012U 59001B   26203.97736659  .00000168  00000+0  80712-4 0  9999",
        "2 00012  32.9092  99.0367 1646912 294.7621  49.0589 11.48626041535443",
    ),
    3: (
        "ECHO 1 DEB",
        "1 00051U 60009C   26204.70015802 -.00000059  00000+0  24388-3 0  9990",
        "2 00051  47.2138 296.3753 0107574 304.4861  54.5805 12.18381511935621",
    ),
}


def record(object_type=1):
    name, tle1, tle2 = TLES[object_type]
    return {"name": name, "type": object_type, "tle1": tle1, "tle2": tle2}


def metadata(count):
    return {
        "fetched_at": "2026-07-24T07:00:00+00:00",
        "expires_at": "2026-07-25T07:00:00+00:00",
        "record_count": count,
        "stale": False,
        "source": "keeptrack_v4_sats_brief",
        "cache_hit": True,
        "latency_ms": 0,
        "etag": None,
    }


def test_catalogue_normalization_and_classification():
    assert keeptrack.classify_object_type(record(1)) == "active_satellite"
    assert keeptrack.classify_object_type(record(2)) == "rocket_body"
    assert keeptrack.classify_object_type(record(3)) == "debris"
    assert keeptrack.has_valid_tle(record())
    assert not keeptrack.has_valid_tle({**record(), "tle2": "invalid"})


def test_configured_2000_object_limit(monkeypatch):
    monkeypatch.delenv("ORBITAL_OBJECT_LIMIT", raising=False)
    records = [record((index % 3) + 1) for index in range(2500)]
    assert keeptrack.configured_object_limit() == 2000
    assert len(keeptrack.select_balanced_records(records, 2000)) == 2000


def test_successful_sgp4_propagation():
    result = propagate_tle(
        TLES[1][1], TLES[1][2],
        datetime(2026, 7, 24, tzinfo=timezone.utc),
    )
    assert result is not None
    assert result["method"] == "sgp4"
    assert result["propagated_at"].endswith("+00:00")


@pytest.mark.asyncio
async def test_24_hour_cache_hit(monkeypatch):
    keeptrack.clear_catalogue_cache()
    calls = 0

    async def upstream():
        nonlocal calls
        calls += 1
        return [record()], {"etag": "test"}

    monkeypatch.setattr(keeptrack, "_fetch_upstream_catalogue", upstream)
    _, miss = await keeptrack.fetch_catalogue()
    _, hit = await keeptrack.fetch_catalogue()
    assert calls == 1
    assert miss["cache_hit"] is False
    assert hit["cache_hit"] is True
    assert hit["expires_at"] == (
        datetime.fromisoformat(hit["fetched_at"]) + timedelta(hours=24)
    ).isoformat()


@pytest.mark.asyncio
async def test_stale_cache_fallback(monkeypatch):
    keeptrack.clear_catalogue_cache()
    keeptrack._catalogue_cache.update({
        "records": [record()],
        "fetched_at": datetime.now(timezone.utc) - timedelta(days=2),
        "expires_at": datetime.now(timezone.utc) - timedelta(days=1),
    })

    async def failure():
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(keeptrack, "_fetch_upstream_catalogue", failure)
    records, cache = await keeptrack.fetch_catalogue()
    assert records == [record()]
    assert cache["stale"] is True
    assert cache["source"] == "keeptrack_v4_sats_brief"


@pytest.mark.asyncio
async def test_objects_schema_and_no_position_fallback(monkeypatch):
    import main
    import routers.objects as objects_router

    records = [record(1), record(2), record(3), {**record(1), "tle2": "invalid"}]

    async def catalogue():
        return records, metadata(len(records))

    async def no_asteroids(start_date, end_date):
        return None

    monkeypatch.setattr(objects_router, "fetch_catalogue", catalogue)
    monkeypatch.setattr(objects_router, "fetch_asteroid_feed", no_asteroids)
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/objects?limit=100")
    assert response.status_code == 200
    payload = response.json()
    assert payload["synthetic_objects"] == 0
    assert payload["propagation_rejected"] == 0
    assert len(payload["objects"]) == 3
    assert {item["category"] for item in payload["objects"]} == {
        "active_satellite", "debris", "rocket_body",
    }
    for item in payload["objects"]:
        assert item["position_mode"] == "sgp4"
        assert item["sgp4_propagation"]
        OrbitalObject.model_validate(item)


@pytest.mark.asyncio
async def test_propagation_failures_are_excluded(monkeypatch):
    import routers.objects as objects_router

    monkeypatch.setattr(objects_router, "propagate_tle", lambda *args: None)
    assert objects_router._satellite_to_object(record()) is None
