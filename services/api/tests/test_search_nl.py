"""API integration tests for natural-language POST /search with mocked LLM and DB session."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.search.query_parser import QueryParserError
from app.search.schemas import SearchPreferences


def _make_provider(
    *,
    name: str,
    specialty_slug: str,
    language_codes: list[str],
    price_min: float,
    price_max: float,
    verification_status: str = "verified",
    is_24x7: bool = True,
):
    prov_id = uuid.uuid4()
    spec = SimpleNamespace(slug=specialty_slug, name=specialty_slug.title())
    doc_langs = [
        SimpleNamespace(language=SimpleNamespace(code=code, name=code.upper()), proficiency="fluent")
        for code in language_codes
    ]
    doctor = SimpleNamespace(specialty=spec, doctor_languages=doc_langs)
    service = SimpleNamespace(name="general_consultation", price_min=price_min, price_max=price_max)
    return SimpleNamespace(
        id=prov_id,
        name=name,
        type="clinic",
        address="123 Main Rd",
        location=None,
        opening_hours={"24x7": True} if is_24x7 else {"mon": []},
        timezone="Asia/Kolkata",
        walk_in_available=False,
        verification_status=verification_status,
        doctors=[doctor],
        services=[service],
    )


class _FakeDB:
    def __init__(self, provider_rows, rating_rows, lang_rows):
        self._calls = 0
        self._provider_rows = provider_rows
        self._rating_rows = rating_rows
        self._lang_rows = lang_rows
        self.added = []

    async def execute(self, stmt):
        self._calls += 1
        if self._calls == 1:
            return SimpleNamespace(all=lambda: self._provider_rows)
        if self._calls == 2:
            return SimpleNamespace(all=lambda: self._rating_rows)
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: self._lang_rows))

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None


def test_nl_search_enforces_hard_constraints_and_ranks():
    p1 = _make_provider(
        name="Dr. Rao Clinic",
        specialty_slug="pediatrics",
        language_codes=["hi", "en"],
        price_min=600,
        price_max=800,
        verification_status="verified",
    )
    p2 = _make_provider(
        name="Expensive Clinic",
        specialty_slug="pediatrics",
        language_codes=["hi"],
        price_min=1500,
        price_max=2000,
        verification_status="verified",
    )
    p3 = _make_provider(
        name="Unverified Clinic",
        specialty_slug="pediatrics",
        language_codes=["hi"],
        price_min=400,
        price_max=500,
        verification_status="pending",
    )

    fake_db = _FakeDB(
        provider_rows=[
            SimpleNamespace(Provider=p1, distance_m=2000.0),
            SimpleNamespace(Provider=p2, distance_m=1000.0),
            SimpleNamespace(Provider=p3, distance_m=500.0),
        ],
        rating_rows=[SimpleNamespace(provider_id=p1.id, avg_rating=4.7, review_count=12)],
        lang_rows=[SimpleNamespace(code="hi", name="Hindi"), SimpleNamespace(code="en", name="English")],
    )

    async def override_get_db():
        yield fake_db

    parsed = SearchPreferences(
        specialty="pediatrics",
        languages=["Hindi"],
        radius_km=5.0,
        budget_max=1000.0,
        verification_required=True,
        hard_constraints=["specialty:pediatrics", "language:Hindi", "budget_max:1000", "verification:verified"],
        ranking_profile="budget_focused",
    )

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.search.service.parse_search_query", AsyncMock(return_value=parsed)):
            client = TestClient(app)
            resp = client.post(
                "/search",
                json={
                    "lat": 15.4909,
                    "lng": 73.8278,
                    "query": "Find a verified Hindi pediatrician within 5 km under ₹1,000",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["results"][0]["name"] == "Dr. Rao Clinic"
        assert data["applied_profile"] == "budget_focused"
        assert "Verified provider" in data["results"][0]["match_reasons"]
    finally:
        app.dependency_overrides.clear()


def test_nl_search_honest_no_results_with_limiting_constraints():
    p1 = _make_provider(
        name="Dental Care",
        specialty_slug="dental",
        language_codes=["en"],
        price_min=500,
        price_max=700,
    )
    fake_db = _FakeDB(
        provider_rows=[SimpleNamespace(Provider=p1, distance_m=1000.0)],
        rating_rows=[],
        lang_rows=[SimpleNamespace(code="en", name="English")],
    )

    async def override_get_db():
        yield fake_db

    parsed = SearchPreferences(
        specialty="cardiology",
        languages=["Hindi"],
        radius_km=5.0,
        hard_constraints=["specialty:cardiology", "language:Hindi", "radius_km:5"],
    )

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.search.service.parse_search_query", AsyncMock(return_value=parsed)):
            client = TestClient(app)
            resp = client.post(
                "/search",
                json={"lat": 15.49, "lng": 73.82, "query": "Hindi cardiologist within 5 km"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["results"] == []
        assert len(data["limiting_constraints"]) > 0
    finally:
        app.dependency_overrides.clear()


def test_nl_search_missing_location_returns_clarification():
    fake_db = _FakeDB(provider_rows=[], rating_rows=[], lang_rows=[])

    async def override_get_db():
        yield fake_db

    parsed = SearchPreferences(
        specialty="pediatrics",
        needs_clarification=True,
        clarification_reason="Current location is required to search within 200 metres.",
    )
    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.search.service.parse_search_query", AsyncMock(return_value=parsed)):
            client = TestClient(app)
            resp = client.post(
                "/search",
                json={"query": "Find a pediatrician within 200 metres of my current location"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["clarification_needed"] is True
        assert data["total"] == 0
    finally:
        app.dependency_overrides.clear()


def test_nl_search_llm_failure_returns_controlled_error():
    fake_db = _FakeDB(provider_rows=[], rating_rows=[], lang_rows=[])

    async def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch(
            "app.search.service.parse_search_query",
            AsyncMock(side_effect=QueryParserError("openrouter_unavailable", "LLM down", status_code=503)),
        ):
            client = TestClient(app)
            resp = client.post(
                "/search",
                json={"lat": 15.49, "lng": 73.82, "query": "Find a cardiologist"},
            )
        assert resp.status_code == 503
        assert resp.json()["detail"]["error"] == "openrouter_unavailable"
    finally:
        app.dependency_overrides.clear()
