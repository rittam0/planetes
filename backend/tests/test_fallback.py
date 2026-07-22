import sys
sys.path.insert(0, '../')

import pytest
from services.nasa import fetch_asteroid_feed
from services.keeptrack import fetch_satellites

@pytest.mark.asyncio
async def test_nasa_returns_data_with_valid_key():
    """NASA should return real data when key is valid"""
    result = await fetch_asteroid_feed("2026-07-22", "2026-07-29")
    assert result is not None
    assert "near_earth_objects" in result
    assert result.get("_source") == "nasa"

@pytest.mark.asyncio
async def test_keeptrack_returns_satellites_with_valid_key():
    """KeepTrack should return satellites when key is valid"""
    result = await fetch_satellites(limit=2)
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0].get("_source") == "keeptrack"
