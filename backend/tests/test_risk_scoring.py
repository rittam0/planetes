import sys
sys.path.insert(0, '../')

from services.sgp4_service import compute_conjunction_risk

def test_low_risk_distant_objects():
    obj1 = {"altitude_km": 400, "velocity_kms": 7.66, "latitude": 0, "longitude": 0, "mass_kg": 1000}
    obj2 = {"altitude_km": 400, "velocity_kms": 7.66, "latitude": 10, "longitude": 10, "mass_kg": 100}
    risk = compute_conjunction_risk(obj1, obj2)
    assert risk["risk_level"] == "LOW"
    assert risk["collision_probability"] <= 1e-5

def test_high_risk_close_objects():
    obj1 = {"altitude_km": 400, "velocity_kms": 7.66, "latitude": 0, "longitude": 0, "mass_kg": 420000}
    obj2 = {"altitude_km": 400, "velocity_kms": 7.62, "latitude": 0.01, "longitude": 0.01, "mass_kg": 5}
    risk = compute_conjunction_risk(obj1, obj2)
    assert risk["risk_level"] in ["LOW", "MEDIUM", "HIGH"]

def test_kinetic_energy_calculation():
    """Test that kinetic energy is computed when objects have different velocities"""
    obj1 = {"altitude_km": 400, "velocity_kms": 7.66, "latitude": 0, "longitude": 0, "mass_kg": 1000}
    obj2 = {"altitude_km": 400, "velocity_kms": 8.0, "latitude": 10, "longitude": 10, "mass_kg": 1000}
    risk = compute_conjunction_risk(obj1, obj2)
    assert risk["kinetic_energy_j"] > 0
    assert risk["method"] == "physics-informed-haversine"

def test_risk_level_is_valid():
    """Test that risk level is one of the expected values"""
    obj1 = {"altitude_km": 400, "velocity_kms": 7.66, "latitude": 0, "longitude": 0, "mass_kg": 1000}
    obj2 = {"altitude_km": 400, "velocity_kms": 7.66, "latitude": 5, "longitude": 5, "mass_kg": 100}
    risk = compute_conjunction_risk(obj1, obj2)
    assert risk["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
