"""Unit tests for LLM query parser, Pydantic validation, and deterministic normalization."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from openai import APITimeoutError, RateLimitError
from pydantic import ValidationError

from app.config import Settings
from app.search.normalizer import (
    metres_to_km,
    miles_to_km,
    normalize_language_code,
    normalize_preferences,
    normalize_specialty,
)
from app.search.query_parser import QueryParserError, extract_json_object, parse_search_query
from app.search.schemas import SearchPreferences


def _mock_client_with_content(content: str):
    msg = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=msg)
    resp = SimpleNamespace(choices=[choice])
    create_mock = AsyncMock(return_value=resp)
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock)))


class TestDeterministicNormalization:
    def test_specialty_synonyms(self):
        assert normalize_specialty("Heart specialist") == "cardiology"
        assert normalize_specialty("Skin doctor") == "dermatology"
        assert normalize_specialty("Children's doctor") == "pediatrics"
        assert normalize_specialty("Family doctor") == "general_physician"
        assert normalize_specialty("general_practice") == "general_physician"

    def test_unit_conversions(self):
        assert miles_to_km(5) == 8.05
        assert miles_to_km(3) == 4.83
        assert metres_to_km(200) == 0.2

    def test_language_normalization(self):
        assert normalize_language_code("Hindi") == "hi"
        assert normalize_language_code("Konkani") == "kok"
        assert normalize_language_code("en") == "en"

    def test_numeric_hints_fill_missing_radius_and_budget(self):
        prefs = SearchPreferences(specialty="dermatology", languages=["English"])
        norm = normalize_preferences(
            prefs, raw_query="Find a skin doctor within 5 miles no more than ₹1,000"
        )
        assert norm.specialty == "dermatology"
        assert norm.radius_km == 8.05
        assert norm.budget_max == 1000.0


class TestSearchPreferencesValidation:
    def test_rejects_unexpected_fields(self):
        with pytest.raises(ValidationError):
            SearchPreferences.model_validate({"specialty": "cardiology", "invented_field": 123})

    def test_rejects_negative_numeric_values(self):
        with pytest.raises(ValidationError):
            SearchPreferences(radius_km=-2.0)
        with pytest.raises(ValidationError):
            SearchPreferences(budget_max=-100.0)
        with pytest.raises(ValidationError):
            SearchPreferences(min_experience_years=-1.0)

    def test_rejects_invalid_ranking_profile(self):
        with pytest.raises(ValidationError):
            SearchPreferences.model_validate({"ranking_profile": "arbitrary_llm_profile"})

    def test_rejects_invalid_availability(self):
        with pytest.raises(ValidationError):
            SearchPreferences.model_validate({"availability": "next_month_maybe"})

    def test_accepts_tomorrow_time_slot(self):
        prefs = SearchPreferences.model_validate({"availability": "tomorrow_09:15"})
        assert prefs.availability == "tomorrow_09:15"


class TestQueryParserWithMockOpenRouter:
    async def test_parses_hindi_cardiologist_query(self):
        payload = {
            "specialty": "cardiologist",
            "languages": ["Hindi"],
            "language_mode": "any",
            "location": None,
            "radius_km": 5,
            "budget_max": None,
            "budget_exact": None,
            "min_experience_years": None,
            "availability": "open_now",
            "verification_required": False,
            "hard_constraints": ["specialty:cardiology", "language:Hindi", "radius_km:5", "availability:open_now"],
            "preferences": [],
            "ranking_profile": "balanced",
            "needs_clarification": False,
            "clarification_reason": None,
            "unanswerable": False,
            "unanswerable_reason": None,
        }
        client = _mock_client_with_content(json.dumps(payload))
        settings = Settings(openrouter_api_key="test-key", llm_search_enabled=True)

        result = await parse_search_query(
            "Find a Hindi-speaking cardiologist within 5 km who is open now.",
            client=client,
            settings=settings,
        )
        assert result.specialty == "cardiology"
        assert result.languages == ["Hindi"]
        assert result.radius_km == 5.0
        assert result.availability == "open_now"
        assert result.ranking_profile == "balanced"

    async def test_parses_alternative_languages_any_mode(self):
        payload = {
            "specialty": None,
            "languages": ["Hindi", "Konkani"],
            "language_mode": "any",
            "min_experience_years": 10,
            "preferences": ["experience"],
            "ranking_profile": "experience_focused",
        }
        client = _mock_client_with_content(json.dumps(payload))
        settings = Settings(openrouter_api_key="test-key", llm_search_enabled=True)

        result = await parse_search_query(
            "Find a doctor who speaks Hindi or Konkani, preferably with at least 10 years of experience.",
            client=client,
            settings=settings,
        )
        assert result.languages == ["Hindi", "Konkani"]
        assert result.language_mode == "any"
        assert result.ranking_profile == "experience_focused"

    async def test_rejects_malformed_json_output(self):
        client = _mock_client_with_content("Here is your doctor: not valid json at all")
        settings = Settings(openrouter_api_key="test-key", llm_search_enabled=True)

        with pytest.raises(QueryParserError) as exc_info:
            await parse_search_query("Find a doctor", client=client, settings=settings)
        assert exc_info.value.code == "invalid_llm_output"
        assert exc_info.value.status_code == 502

    async def test_rejects_unexpected_field_from_llm(self):
        client = _mock_client_with_content(json.dumps({"specialty": "cardiology", "hack": True}))
        settings = Settings(openrouter_api_key="test-key", llm_search_enabled=True)

        with pytest.raises(QueryParserError) as exc_info:
            await parse_search_query("Find a cardiologist", client=client, settings=settings)
        assert exc_info.value.code == "invalid_llm_output"

    async def test_missing_api_key_raises_controlled_error(self):
        settings = Settings(openrouter_api_key=None, llm_search_enabled=True)
        with pytest.raises(QueryParserError) as exc_info:
            await parse_search_query("Find a doctor", settings=settings)
        assert exc_info.value.code == "missing_api_key"
        assert exc_info.value.status_code == 503

    async def test_retries_transient_timeout_then_succeeds(self):
        req = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        payload = {"specialty": "dermatology", "languages": ["English"], "ranking_profile": "nearest"}
        msg = SimpleNamespace(content=json.dumps(payload))
        resp = SimpleNamespace(choices=[SimpleNamespace(message=msg)])

        create_mock = AsyncMock(side_effect=[APITimeoutError(request=req), resp])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock)))
        settings = Settings(openrouter_api_key="test-key", openrouter_max_retries=2)

        result = await parse_search_query("English skin doctor nearby", client=client, settings=settings)
        assert result.specialty == "dermatology"
        assert create_mock.await_count == 2

    async def test_bounded_retry_exhausted_on_rate_limit(self):
        req = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        http_resp = httpx.Response(429, request=req)
        rate_err = RateLimitError("rate limited", response=http_resp, body=None)
        create_mock = AsyncMock(side_effect=rate_err)
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock)))
        settings = Settings(openrouter_api_key="test-key", openrouter_max_retries=1)

        with pytest.raises(QueryParserError) as exc_info:
            await parse_search_query("Find a doctor", client=client, settings=settings)
        assert exc_info.value.code == "openrouter_rate_limited"
        assert exc_info.value.status_code == 429
        assert create_mock.await_count == 2

    def test_extract_json_strips_markdown_fences(self):
        parsed = extract_json_object('```json\n{"specialty": "cardiology"}\n```')
        assert parsed == {"specialty": "cardiology"}
