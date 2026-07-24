import importlib

import httpx
import pytest


def test_application_imports_without_groq_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    module = importlib.import_module("main")
    assert module.app.title == "Planetes Backend"


@pytest.mark.asyncio
async def test_object_failures_return_explicit_degraded_status(monkeypatch):
    import routers.objects as objects_router

    async def no_satellites(limit=30):
        return []

    async def no_asteroids(start_date, end_date):
        return None

    monkeypatch.setattr(objects_router, "fetch_satellites", no_satellites)
    monkeypatch.setattr(objects_router, "fetch_asteroid_feed", no_asteroids)
    transport = httpx.ASGITransport(app=importlib.import_module("main").app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/objects")
    payload = response.json()
    assert payload["data_status"] == "degraded"
    assert set(payload["degraded_sources"]) == {"keeptrack", "nasa"}
    assert payload["objects"] == []
    assert payload["synthetic_objects"] == 0


@pytest.mark.asyncio
async def test_asteroid_failure_has_no_mock_success(monkeypatch):
    import routers.asteroids as asteroid_router

    async def no_asteroids(start_date, end_date):
        return None

    monkeypatch.setattr(asteroid_router, "fetch_asteroid_feed", no_asteroids)
    transport = httpx.ASGITransport(app=importlib.import_module("main").app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/asteroids")
    payload = response.json()
    assert payload["data_status"] == "degraded"
    assert payload["degraded_data"] is True
    assert payload["objects"] == []


@pytest.mark.asyncio
async def test_conjunction_endpoint_does_not_return_fabricated_events():
    transport = httpx.ASGITransport(app=importlib.import_module("main").app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/conjunctions")
    payload = response.json()
    assert payload["data_status"] == "unavailable"
    assert payload["encounters"] == []
