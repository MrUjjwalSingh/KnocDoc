"""Matching engine — rule-based provider scoring."""
from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pytz
import yaml


_WEIGHTS_PATH = Path(__file__).parent / "weights.yaml"
_config: dict | None = None


def _load_config() -> dict:
    global _config
    if _config is None:
        with open(_WEIGHTS_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


def get_weights() -> dict:
    return _load_config()["weights"]


def get_need_to_specialty(need_category: str) -> list[str]:
    cfg = _load_config()
    return cfg["need_to_specialty"].get(need_category, ["general_physician"])


def get_max_radius_km() -> float:
    cfg = _load_config()
    return cfg["distance"]["max_radius_km"]


def get_default_rating_score() -> float:
    cfg = _load_config()
    return cfg["rating"]["default_when_no_reviews"]


# ---------------------------------------------------------------------------
# Individual sub-scorers
# ---------------------------------------------------------------------------

def compute_distance_score(distance_km: float, max_radius_km: float | None = None) -> float:
    """Score 1.0 at 0 km, 0.0 at max_radius_km, negative clamped to 0."""
    if max_radius_km is None:
        max_radius_km = get_max_radius_km()
    if distance_km < 0:
        return 0.0
    return max(0.0, 1.0 - distance_km / max_radius_km)


def compute_language_score(
    provider_language_codes: list[str],
    requested_language_code: str,
) -> float:
    """
    1.0  — provider has at least one doctor who speaks the requested language
    0.7  — no match but at least one English-speaking doctor
    0.0  — no English either
    """
    codes_lower = [c.lower() for c in provider_language_codes]
    requested_lower = requested_language_code.lower()

    if requested_lower in codes_lower:
        return 1.0
    if requested_lower != "en" and "en" in codes_lower:
        return 0.7
    return 0.0


def compute_open_now_score(
    opening_hours: dict,
    timezone_str: str,
    walk_in_available: bool,
    now: datetime | None = None,
) -> float:
    """
    1.0  — open right now (or 24x7)
    0.5  — closed per schedule but walk_in_available=True
    0.0  — closed, no walk-in
    """
    if opening_hours.get("24x7"):
        return 1.0

    if now is None:
        try:
            tz = pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            tz = pytz.UTC
        now = datetime.now(tz)

    # Ensure now is timezone-aware in the provider's timezone
    try:
        tz = pytz.timezone(timezone_str)
        if now.tzinfo is None:
            now = tz.localize(now)
        else:
            now = now.astimezone(tz)
    except pytz.exceptions.UnknownTimeZoneError:
        pass

    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_key = day_names[now.weekday()]
    day_hours = opening_hours.get(day_key, [])

    current_minutes = now.hour * 60 + now.minute

    for slot in day_hours:
        try:
            open_h, open_m = map(int, slot["open"].split(":"))
            close_h, close_m = map(int, slot["close"].split(":"))
            open_minutes = open_h * 60 + open_m
            close_minutes = close_h * 60 + close_m
            if open_minutes <= current_minutes < close_minutes:
                return 1.0
        except (KeyError, ValueError):
            continue

    return 0.5 if walk_in_available else 0.0


def compute_specialty_score(
    doctor_specialty_slugs: list[str],
    need_category: str,
) -> float:
    """
    1.0  — a doctor has the exact specialty for the need
    0.5  — only general_physician available
    0.0  — no matching specialty
    """
    target_specialties = get_need_to_specialty(need_category)
    primary_target = target_specialties[0] if target_specialties else "general_physician"

    slugs_lower = [s.lower() for s in doctor_specialty_slugs]

    # Exact match on any target specialty
    for target in target_specialties:
        if target.lower() in slugs_lower:
            return 1.0

    # Fallback: general_physician available
    if "general_physician" in slugs_lower:
        return 0.5

    return 0.0


def compute_verification_score(verification_status: str) -> float:
    if verification_status == "verified":
        return 1.0
    if verification_status == "pending":
        return 0.3
    return 0.0  # rejected


def compute_rating_score(
    average_rating: float | None,
    max_rating: float = 5.0,
) -> float:
    if average_rating is None:
        return get_default_rating_score()
    return max(0.0, min(1.0, average_rating / max_rating))


# ---------------------------------------------------------------------------
# Composite scorer
# ---------------------------------------------------------------------------

def compute_score(
    distance_km: float,
    language_codes: list[str],
    requested_language: str,
    opening_hours: dict,
    timezone_str: str,
    walk_in_available: bool,
    specialty_slugs: list[str],
    need_category: str,
    verification_status: str,
    average_rating: float | None,
    now: datetime | None = None,
    max_radius_km: float | None = None,
) -> tuple[float, dict[str, float]]:
    """
    Returns (final_score_0_to_100, sub_scores_dict).
    """
    weights = get_weights()
    if max_radius_km is None:
        max_radius_km = get_max_radius_km()

    sub_scores = {
        "distance": compute_distance_score(distance_km, max_radius_km),
        "language": compute_language_score(language_codes, requested_language),
        "open_now": compute_open_now_score(opening_hours, timezone_str, walk_in_available, now),
        "specialty": compute_specialty_score(specialty_slugs, need_category),
        "verification": compute_verification_score(verification_status),
        "rating": compute_rating_score(average_rating),
    }

    final = 100.0 * (
        weights["distance"] * sub_scores["distance"]
        + weights["language"] * sub_scores["language"]
        + weights["open_now"] * sub_scores["open_now"]
        + weights["specialty"] * sub_scores["specialty"]
        + weights["verification"] * sub_scores["verification"]
        + weights["rating"] * sub_scores["rating"]
    )

    return round(final, 2), sub_scores


def build_match_reasons(
    sub_scores: dict[str, float],
    distance_km: float,
    requested_language: str,
    language_names: dict[str, str],
    need_category: str,
) -> list[str]:
    """Build human-readable match reasons for UI display."""
    reasons: list[str] = []

    # Distance
    if sub_scores["distance"] > 0:
        reasons.append(f"{distance_km:.1f} km away")

    # Language
    lang_score = sub_scores["language"]
    if lang_score == 1.0:
        lang_name = language_names.get(requested_language.lower(), requested_language.upper())
        reasons.append(f"Speaks {lang_name}")
    elif lang_score == 0.7:
        reasons.append("English-speaking doctor available")

    # Open now
    open_score = sub_scores["open_now"]
    if open_score == 1.0:
        reasons.append("Open now")
    elif open_score == 0.5:
        reasons.append("Walk-in accepted")

    # Specialty
    spec_score = sub_scores["specialty"]
    if spec_score == 1.0:
        cfg = _load_config()
        need_label = cfg.get("need_labels", {}).get(need_category, need_category)
        reasons.append(f"Specialist for {need_label}")
    elif spec_score == 0.5:
        reasons.append("General physician available")

    # Verification
    if sub_scores["verification"] == 1.0:
        reasons.append("Verified provider")

    return reasons

