"""Unit tests for preference-aware ranking profiles, cost scoring, and hard constraints."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.matching.engine import (
    ALLOWED_PROFILES,
    compute_cost_score,
    compute_language_score,
    compute_score,
    get_profile_weights,
)
from app.search.schemas import SearchPreferences
from app.search.service import passes_hard_constraints


class TestRankingProfiles:
    @pytest.mark.parametrize("profile", ALLOWED_PROFILES)
    def test_profile_weights_are_non_negative_and_sum_to_one(self, profile: str):
        weights = get_profile_weights(profile)
        assert all(v >= 0.0 for v in weights.values())
        assert pytest.approx(sum(weights.values()), 1e-6) == 1.0

    def test_invalid_profile_raises(self):
        with pytest.raises(ValueError):
            get_profile_weights("unrestricted_llm_weights")

    def test_nearest_vs_budget_profile_ordering(self):
        # Provider A: closer (1 km) but expensive (1500)
        # Provider B: farther (6 km) but affordable (300)
        score_a_near, _ = compute_score(
            distance_km=1.0,
            language_codes=["en"],
            requested_language="en",
            opening_hours={"24x7": True},
            timezone_str="Asia/Kolkata",
            walk_in_available=True,
            specialty_slugs=["dermatology"],
            need_category="skin_problem",
            verification_status="verified",
            average_rating=4.5,
            max_radius_km=10.0,
            profile="nearest",
            requested_specialty="dermatology",
            min_price=1500.0,
        )
        score_b_near, _ = compute_score(
            distance_km=6.0,
            language_codes=["en"],
            requested_language="en",
            opening_hours={"24x7": True},
            timezone_str="Asia/Kolkata",
            walk_in_available=True,
            specialty_slugs=["dermatology"],
            need_category="skin_problem",
            verification_status="verified",
            average_rating=4.5,
            max_radius_km=10.0,
            profile="nearest",
            requested_specialty="dermatology",
            min_price=300.0,
        )
        assert score_a_near > score_b_near

        score_a_budget, _ = compute_score(
            distance_km=1.0,
            language_codes=["en"],
            requested_language="en",
            opening_hours={"24x7": True},
            timezone_str="Asia/Kolkata",
            walk_in_available=True,
            specialty_slugs=["dermatology"],
            need_category="skin_problem",
            verification_status="verified",
            average_rating=4.5,
            max_radius_km=10.0,
            profile="budget_focused",
            requested_specialty="dermatology",
            min_price=1500.0,
        )
        score_b_budget, _ = compute_score(
            distance_km=6.0,
            language_codes=["en"],
            requested_language="en",
            opening_hours={"24x7": True},
            timezone_str="Asia/Kolkata",
            walk_in_available=True,
            specialty_slugs=["dermatology"],
            need_category="skin_problem",
            verification_status="verified",
            average_rating=4.5,
            max_radius_km=10.0,
            profile="budget_focused",
            requested_specialty="dermatology",
            min_price=300.0,
        )
        assert score_b_budget > score_a_budget


class TestCostAndMissingDataScoring:
    def test_missing_price_never_gets_max_score(self):
        assert compute_cost_score(None) == 0.0
        assert compute_cost_score(None, budget_max=1000.0) == 0.0

    def test_lower_cost_scores_higher_within_budget(self):
        low = compute_cost_score(300.0, budget_max=1000.0)
        high = compute_cost_score(900.0, budget_max=1000.0)
        over = compute_cost_score(1200.0, budget_max=1000.0)
        assert low > high > over
        assert over == 0.0

    def test_alternative_languages_any_vs_all(self):
        assert compute_language_score(["hi"], "hi", requested_languages=["hi", "kok"], language_mode="any") == 1.0
        assert compute_language_score(["hi"], "hi", requested_languages=["hi", "kok"], language_mode="all") == 0.5
        assert compute_language_score(["hi", "kok"], "hi", requested_languages=["hi", "kok"], language_mode="all") == 1.0


class TestHardConstraintsEnforcement:
    def test_unverified_provider_rejected_when_verification_required(self):
        prefs = SearchPreferences(verification_required=True)
        ok, failed = passes_hard_constraints(
            specialty_slugs=["pediatrics"],
            language_codes=["hi"],
            services=[SimpleNamespace(name="general_consultation", price_min=500, price_max=700)],
            opening_hours={"24x7": True},
            timezone_str="Asia/Kolkata",
            walk_in_available=True,
            verification_status="pending",
            prefs=prefs,
        )
        assert not ok
        assert "verification:verified" in failed

    def test_budget_constraint_blocks_expensive_provider(self):
        prefs = SearchPreferences(budget_max=1000.0)
        ok, failed = passes_hard_constraints(
            specialty_slugs=["pediatrics"],
            language_codes=["hi"],
            services=[SimpleNamespace(name="general_consultation", price_min=1200, price_max=1500)],
            opening_hours={"24x7": True},
            timezone_str="Asia/Kolkata",
            walk_in_available=True,
            verification_status="verified",
            prefs=prefs,
        )
        assert not ok
        assert "budget_max:1000" in failed

    def test_alternative_languages_or_constraint_passes_with_one_match(self):
        prefs = SearchPreferences(languages=["Hindi", "Konkani"], language_mode="any")
        ok, failed = passes_hard_constraints(
            specialty_slugs=["general_physician"],
            language_codes=["kok"],
            services=[SimpleNamespace(name="general_consultation", price_min=400, price_max=600)],
            opening_hours={"24x7": True},
            timezone_str="Asia/Kolkata",
            walk_in_available=True,
            verification_status="verified",
            prefs=prefs,
        )
        assert ok
        assert failed == []
