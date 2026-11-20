"""Tests for FastAPI endpoints and validation."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.matching.engine import get_weights, get_need_to_specialty

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_weights_configuration():
    weights = get_weights()
    expected_keys = {"distance", "language", "open_now", "specialty", "verification", "rating"}
    assert set(weights.keys()) == expected_keys
    assert pytest.approx(sum(weights.values()), 0.001) == 1.0


def test_need_to_specialty_mappings():
    for need in ["fever", "stomach_issue", "injury", "dental_pain", "skin_problem", "ear_nose_throat", "child_health"]:
        specialties = get_need_to_specialty(need)
        assert len(specialties) >= 1


def test_search_validation_invalid_need():
    payload = {
        "lat": 15.4909,
        "lng": 73.8278,
        "language_code": "en",
        "need_category": "invalid_need_xyz",
    }
    response = client.post("/search", json=payload)
    assert response.status_code == 422


def test_search_validation_invalid_coordinates():
    # Lat > 90 is invalid
    payload = {
        "lat": 95.0,
        "lng": 73.8278,
        "language_code": "en",
        "need_category": "fever",
    }
    response = client.post("/search", json=payload)
    assert response.status_code == 422


def test_review_validation_rating_out_of_bounds():
    # Rating 6 is out of bounds (1-5)
    payload = {
        "provider_id": "00000000-0000-0000-0000-000000000000",
        "rating": 6,
    }
    response = client.post("/reviews", json=payload)
    assert response.status_code == 422


def test_events_validation():
    # Missing session_id
    payload = {
        "event_name": "search_submitted",
    }
    response = client.post("/events", json=payload)
    assert response.status_code == 422

