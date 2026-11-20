"""Unit tests for the matching engine scoring rules and edge cases."""
from __future__ import annotations

from datetime import datetime
import pytz
import pytest

from app.matching.engine import (
    build_match_reasons,
    compute_distance_score,
    compute_language_score,
    compute_open_now_score,
    compute_rating_score,
    compute_score,
    compute_specialty_score,
    compute_verification_score,
    get_weights,
)


class TestDistanceScore:
    def test_zero_distance_gives_full_score(self):
        score = compute_distance_score(0.0, max_radius_km=10.0)
        assert score == 1.0

    def test_halfway_distance_gives_half_score(self):
        score = compute_distance_score(5.0, max_radius_km=10.0)
        assert pytest.approx(score, 0.001) == 0.5

    def test_at_max_radius_gives_zero(self):
        score = compute_distance_score(10.0, max_radius_km=10.0)
        assert score == 0.0

    def test_beyond_max_radius_clamped_to_zero(self):
        score = compute_distance_score(15.0, max_radius_km=10.0)
        assert score == 0.0

    def test_negative_distance_clamped_to_zero(self):
        score = compute_distance_score(-1.0, max_radius_km=10.0)
        assert score == 0.0


class TestLanguageScore:
    def test_exact_language_match_gives_one(self):
        score = compute_language_score(["en", "ru"], "ru")
        assert score == 1.0

    def test_case_insensitive_match(self):
        score = compute_language_score(["EN", "HI"], "en")
        assert score == 1.0

    def test_english_fallback_when_requested_language_missing(self):
        score = compute_language_score(["en", "hi"], "fr")
        assert pytest.approx(score, 0.001) == 0.7

    def test_no_match_and_no_english_gives_zero(self):
        score = compute_language_score(["hi", "kok"], "fr")
        assert score == 0.0

    def test_requested_english_missing_gives_zero(self):
        score = compute_language_score(["hi", "kok"], "en")
        assert score == 0.0


class TestOpenNowScore:
    def test_24x7_flag_always_gives_one(self):
        score = compute_open_now_score({"24x7": True}, "Asia/Kolkata", walk_in_available=False)
        assert score == 1.0

    def test_open_within_scheduled_hours(self):
        # Monday 10:00 AM
        tz = pytz.timezone("Asia/Kolkata")
        mon_10am = tz.localize(datetime(2024, 1, 15, 10, 0))  # Jan 15, 2024 was Monday
        hours = {"mon": [{"open": "09:00", "close": "18:00"}]}
        score = compute_open_now_score(hours, "Asia/Kolkata", walk_in_available=False, now=mon_10am)
        assert score == 1.0

    def test_closed_schedule_with_walk_in_gives_half(self):
        # Sunday when closed
        tz = pytz.timezone("Asia/Kolkata")
        sun_10am = tz.localize(datetime(2024, 1, 14, 10, 0))  # Jan 14, 2024 was Sunday
        hours = {"mon": [{"open": "09:00", "close": "18:00"}], "sun": []}
        score = compute_open_now_score(hours, "Asia/Kolkata", walk_in_available=True, now=sun_10am)
        assert score == 0.5

    def test_closed_schedule_without_walk_in_gives_zero(self):
        tz = pytz.timezone("Asia/Kolkata")
        sun_10am = tz.localize(datetime(2024, 1, 14, 10, 0))
        hours = {"mon": [{"open": "09:00", "close": "18:00"}], "sun": []}
        score = compute_open_now_score(hours, "Asia/Kolkata", walk_in_available=False, now=sun_10am)
        assert score == 0.0


class TestSpecialtyScore:
    def test_exact_specialty_match(self):
        score = compute_specialty_score(["pediatrics", "general_physician"], "child_health")
        assert score == 1.0

    def test_general_physician_fallback(self):
        score = compute_specialty_score(["general_physician"], "dental_pain")
        assert score == 0.5

    def test_no_relevant_specialty_gives_zero(self):
        score = compute_specialty_score(["dermatology"], "dental_pain")
        assert score == 0.0

    def test_case_insensitive_specialty(self):
        score = compute_specialty_score(["Dental"], "dental_pain")
        assert score == 1.0


class TestVerificationScore:
    def test_verified_gives_one(self):
        assert compute_verification_score("verified") == 1.0

    def test_pending_gives_point_three(self):
        assert compute_verification_score("pending") == 0.3

    def test_rejected_gives_zero(self):
        assert compute_verification_score("rejected") == 0.0


class TestRatingScore:
    def test_five_star_gives_one(self):
        assert compute_rating_score(5.0) == 1.0

    def test_zero_star_gives_zero(self):
        assert compute_rating_score(0.0) == 0.0

    def test_none_gives_default_half(self):
        assert compute_rating_score(None) == 0.5

    def test_four_star_gives_point_eight(self):
        assert pytest.approx(compute_rating_score(4.0), 0.001) == 0.8


class TestCompositeScorer:
    def test_perfect_provider_scores_100(self):
        score, sub = compute_score(
            distance_km=0.0,
            language_codes=["ru", "en"],
            requested_language="ru",
            opening_hours={"24x7": True},
            timezone_str="Asia/Kolkata",
            walk_in_available=True,
            specialty_slugs=["pediatrics"],
            need_category="child_health",
            verification_status="verified",
            average_rating=5.0,
        )
        assert score == 100.0
        assert all(v == 1.0 for v in sub.values())

    def test_worst_provider_outside_radius_scores_near_zero(self):
        # Outside radius, no language match, closed without walk-in, wrong specialty, pending, 1 star
        score, sub = compute_score(
            distance_km=15.0,  # 0
            language_codes=["hi"],  # 0
            requested_language="fr",
            opening_hours={"mon": []},  # 0
            timezone_str="Asia/Kolkata",
            walk_in_available=False,
            specialty_slugs=["dental"],  # 0 for child_health
            need_category="child_health",
            verification_status="pending",  # 0.3 * 0.05 = 0.015
            average_rating=1.0,  # 0.2 * 0.05 = 0.010
        )
        # 100 * (0.015 + 0.010) = 2.5
        assert score == 2.5

    def test_weights_sum_to_one(self):
        weights = get_weights()
        total_weight = sum(weights.values())
        assert pytest.approx(total_weight, 0.001) == 1.0


class TestMatchReasons:
    def test_builds_expected_reasons(self):
        sub_scores = {
            "distance": 0.8,
            "language": 1.0,
            "open_now": 1.0,
            "specialty": 1.0,
            "verification": 1.0,
            "rating": 0.8,
        }
        reasons = build_match_reasons(
            sub_scores=sub_scores,
            distance_km=2.0,
            requested_language="ru",
            language_names={"ru": "Russian", "en": "English"},
            need_category="fever",
        )
        assert "2.0 km away" in reasons
        assert "Speaks Russian" in reasons
        assert "Open now" in reasons
        assert "Verified provider" in reasons

