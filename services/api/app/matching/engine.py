"""Matching engine — rule-based and profile-aware provider scoring."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytz
import yaml

ALLOWED_PROFILES = ("balanced", "nearest", "budget_focused", "experience_focused")

_WEIGHTS_PATH = Path(__file__).parent / "weights.yaml"
_config: dict | None = None


def _load_config() -> dict:
    global _config
    if _config is None:
        with open(_WEIGHTS_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


def get_weights() -> dict[str, float]:
    return _load_config()["weights"]


def get_profile_weights(profile: str = "balanced") -> dict[str, float]:
    """Return validated weights for a named ranking profile."""
    if profile not in ALLOWED_PROFILES:
        raise ValueError(
            f"Unsupported ranking profile '{profile}'. Allowed: {ALLOWED_PROFILES}"
        )
    profiles = _load_config().get("profiles", {})
    if profile not in profiles:
        raise ValueError(f"Profile '{profile}' is not configured in weights.yaml")
    weights = {k: float(v) for k, v in profiles[profile].items()}
    if any(w < 0 for w in weights.values()):
        raise ValueError(f"Profile '{profile}' contains negative weights")
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Profile '{profile}' weights must sum to 1.0 (got {total})")
    return weights


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


def compute_distance_score(
    distance_km: float, max_radius_km: float | None = None
) -> float:
    """Score 1.0 at 0 km, 0.0 at max_radius_km, negative clamped to 0."""
    if max_radius_km is None:
        max_radius_km = get_max_radius_km()
    if max_radius_km <= 0 or distance_km < 0:
        return 0.0
    return max(0.0, 1.0 - distance_km / max_radius_km)


def compute_language_score(
    provider_language_codes: list[str],
    requested_language_code: str,
    requested_languages: list[str] | None = None,
    language_mode: str = "any",
) -> float:
    """
    1.0  — provider has doctor(s) speaking requested language(s)
    0.7  — no exact match but at least one English-speaking doctor
    0.0  — no match and no English
    """
    codes_lower = {c.lower() for c in provider_language_codes}

    if requested_languages:
        req_lower = [c.lower() for c in requested_languages if c]
        if not req_lower:
            return 1.0 if "en" in codes_lower else 0.5
        if language_mode == "all":
            matched = sum(1 for c in req_lower if c in codes_lower)
            if matched == len(req_lower):
                return 1.0
            if matched > 0:
                return round(matched / len(req_lower), 3)
            return 0.7 if "en" in codes_lower and "en" not in req_lower else 0.0
        # "any" mode: any requested language satisfies 1.0
        if any(c in codes_lower for c in req_lower):
            return 1.0
        if "en" not in req_lower and "en" in codes_lower:
            return 0.7
        return 0.0

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
    0.0  — closed, no walk-in or unknown schedule
    """
    if not opening_hours:
        return 0.5 if walk_in_available else 0.0

    if opening_hours.get("24x7"):
        return 1.0

    if now is None:
        try:
            tz = pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            tz = pytz.UTC
        now = datetime.now(tz)

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
    requested_specialty: str | None = None,
) -> float:
    """
    1.0  — a doctor has the exact specialty for the need/query
    0.5  — only general_physician available
    0.0  — no matching specialty
    """
    slugs_lower = [s.lower() for s in doctor_specialty_slugs]

    if requested_specialty:
        req = requested_specialty.lower()
        if req in slugs_lower:
            return 1.0
        if "general_physician" in slugs_lower:
            return 0.5
        return 0.0

    target_specialties = get_need_to_specialty(need_category)
    for target in target_specialties:
        if target.lower() in slugs_lower:
            return 1.0

    if "general_physician" in slugs_lower:
        return 0.5

    return 0.0


def compute_verification_score(verification_status: str) -> float:
    if verification_status == "verified":
        return 1.0
    if verification_status == "pending":
        return 0.3
    return 0.0


def compute_rating_score(
    average_rating: float | None,
    max_rating: float = 5.0,
) -> float:
    if average_rating is None:
        return get_default_rating_score()
    return max(0.0, min(1.0, average_rating / max_rating))


def compute_cost_score(
    min_price: float | None,
    budget_max: float | None = None,
    reference_max_price: float = 2000.0,
) -> float:
    """
    Score consultation cost in [0, 1], where lower price yields a higher score.
    Missing price data receives 0.0 (never automatically awarded maximum score).
    """
    if min_price is None or min_price < 0:
        return 0.0
    if budget_max is not None and budget_max > 0:
        if min_price > budget_max:
            return 0.0
        return round(max(0.0, min(1.0, 1.0 - 0.5 * (min_price / budget_max))), 4)
    return round(max(0.0, min(1.0, 1.0 - (min_price / reference_max_price))), 4)


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
    *,
    profile: str | None = None,
    requested_languages: list[str] | None = None,
    language_mode: str = "any",
    requested_specialty: str | None = None,
    min_price: float | None = None,
    budget_max: float | None = None,
) -> tuple[float, dict[str, float]]:
    """
    Returns (final_score_0_to_100, sub_scores_dict).
    When `profile` is None, uses legacy `weights` for full backward compatibility.
    """
    if max_radius_km is None:
        max_radius_km = get_max_radius_km()

    sub_scores: dict[str, float] = {
        "distance": compute_distance_score(distance_km, max_radius_km),
        "language": compute_language_score(
            language_codes,
            requested_language,
            requested_languages=requested_languages,
            language_mode=language_mode,
        ),
        "open_now": compute_open_now_score(
            opening_hours, timezone_str, walk_in_available, now
        ),
        "specialty": compute_specialty_score(
            specialty_slugs, need_category, requested_specialty=requested_specialty
        ),
        "verification": compute_verification_score(verification_status),
        "rating": compute_rating_score(average_rating),
    }

    if profile is None:
        weights = get_weights()
    else:
        weights = get_profile_weights(profile)
        sub_scores["cost"] = compute_cost_score(min_price, budget_max=budget_max)

    final = 100.0 * sum(weights[k] * sub_scores[k] for k in weights)
    return round(final, 2), sub_scores


def build_match_reasons(
    sub_scores: dict[str, float],
    distance_km: float,
    requested_language: str,
    language_names: dict[str, str],
    need_category: str,
    *,
    requested_languages: list[str] | None = None,
    provider_language_codes: list[str] | None = None,
    requested_specialty: str | None = None,
    min_price: float | None = None,
    budget_max: float | None = None,
    profile: str | None = None,
) -> list[str]:
    """Build concise, fact-grounded match reasons from database facts and applied rules."""
    reasons: list[str] = []

    if sub_scores["distance"] > 0:
        reasons.append(f"{distance_km:.1f} km away")

    lang_score = sub_scores["language"]
    if lang_score == 1.0:
        if requested_languages and provider_language_codes:
            prov_set = {c.lower() for c in provider_language_codes}
            matched_names = [
                language_names.get(c.lower(), c.upper())
                for c in requested_languages
                if c.lower() in prov_set
            ]
            if matched_names:
                reasons.append(
                    f"Recorded {' / '.join(matched_names)} language proficiency"
                )
        else:
            lang_name = language_names.get(
                requested_language.lower(), requested_language.upper()
            )
            reasons.append(f"Speaks {lang_name}")
    elif lang_score == 0.7:
        reasons.append("English-speaking doctor available")

    open_score = sub_scores["open_now"]
    if open_score == 1.0:
        reasons.append("Open now")
    elif open_score == 0.5:
        reasons.append("Walk-in accepted")

    spec_score = sub_scores["specialty"]
    if spec_score == 1.0:
        if requested_specialty:
            reasons.append(f"Matches requested specialty ({requested_specialty})")
        else:
            cfg = _load_config()
            need_label = cfg.get("need_labels", {}).get(need_category, need_category)
            reasons.append(f"Specialist for {need_label}")
    elif spec_score == 0.5:
        reasons.append("General physician available")

    if min_price is not None and budget_max is not None and min_price <= budget_max:
        reasons.append(f"Consultation fee within ₹{int(budget_max)} budget")
    elif profile == "budget_focused" and min_price is not None:
        reasons.append(f"Consultation from ₹{int(min_price)}")

    if sub_scores["verification"] == 1.0:
        reasons.append("Verified provider")

    if profile == "nearest":
        reasons.append("Prioritized by proximity")
    elif profile == "experience_focused" and sub_scores["verification"] == 1.0:
        reasons.append("Prioritized by verified credentials and ratings")

    return reasons
