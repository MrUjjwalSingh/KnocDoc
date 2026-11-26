"""Deterministic normalization helpers for parsed natural-language queries."""

from __future__ import annotations

import re

from app.search.schemas import SearchPreferences

SPECIALTY_SYNONYMS: dict[str, str] = {
    "cardiology": "cardiology",
    "cardiologist": "cardiology",
    "heart specialist": "cardiology",
    "heart doctor": "cardiology",
    "cardiac": "cardiology",
    "dermatology": "dermatology",
    "dermatologist": "dermatology",
    "skin doctor": "dermatology",
    "skin specialist": "dermatology",
    "skin problem": "dermatology",
    "pediatrics": "pediatrics",
    "paediatrics": "pediatrics",
    "pediatrician": "pediatrics",
    "paediatrician": "pediatrics",
    "child doctor": "pediatrics",
    "children's doctor": "pediatrics",
    "childrens doctor": "pediatrics",
    "child specialist": "pediatrics",
    "child health": "pediatrics",
    "general_physician": "general_physician",
    "general physician": "general_physician",
    "general_practice": "general_physician",
    "general practice": "general_physician",
    "general practitioner": "general_physician",
    "family doctor": "general_physician",
    "gp": "general_physician",
    "physician": "general_physician",
    "dental": "dental",
    "dentist": "dental",
    "dental pain": "dental",
    "tooth doctor": "dental",
    "orthopedic": "orthopedic",
    "orthopaedic": "orthopedic",
    "orthopedist": "orthopedic",
    "bone doctor": "orthopedic",
    "gastroenterology": "gastroenterology",
    "gastroenterologist": "gastroenterology",
    "stomach doctor": "gastroenterology",
    "ent": "ent",
    "ear nose throat": "ent",
    "ear, nose & throat": "ent",
    "ent specialist": "ent",
    "emergency_care": "emergency_care",
    "emergency care": "emergency_care",
    "emergency": "emergency_care",
    "urgent care": "emergency_care",
}

LANGUAGE_NAME_TO_CODE: dict[str, str] = {
    "english": "en",
    "en": "en",
    "hindi": "hi",
    "hi": "hi",
    "russian": "ru",
    "ru": "ru",
    "arabic": "ar",
    "ar": "ar",
    "french": "fr",
    "fr": "fr",
    "german": "de",
    "de": "de",
    "konkani": "kok",
    "kok": "kok",
    "tamil": "ta",
    "ta": "ta",
    "marathi": "mr",
    "mr": "mr",
    "japanese": "ja",
    "ja": "ja",
}

LANGUAGE_CODE_TO_NAME: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "ru": "Russian",
    "ar": "Arabic",
    "fr": "French",
    "de": "German",
    "kok": "Konkani",
    "ta": "Tamil",
    "mr": "Marathi",
    "ja": "Japanese",
}

_MILES_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:miles?|mi)\b", re.IGNORECASE)
_METRES_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m)\b", re.IGNORECASE)
_KM_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(?:km|kilometres?|kilometers?)\b", re.IGNORECASE
)
_BUDGET_MAX_RE = re.compile(
    r"(?:under|below|less than|no more than|at most|max(?:imum)?|budget(?:\s+is)?|up to)\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)
_EXACT_BUDGET_RE = re.compile(
    r"(?:exactly)\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)


def normalize_specialty(raw: str | None) -> str | None:
    """Normalize common specialty phrases to canonical slugs."""
    if not raw:
        return None
    cleaned = raw.strip().lower()
    if cleaned in SPECIALTY_SYNONYMS:
        return SPECIALTY_SYNONYMS[cleaned]
    underscored = cleaned.replace(" ", "_").replace("-", "_")
    if underscored in SPECIALTY_SYNONYMS:
        return SPECIALTY_SYNONYMS[underscored]
    return raw.strip()


def normalize_language_code(raw: str) -> str:
    """Normalize a language name or code to its lowercase code when known."""
    cleaned = raw.strip().lower()
    return LANGUAGE_NAME_TO_CODE.get(cleaned, cleaned)


def normalize_language_name(raw: str) -> str:
    """Normalize a language name or code to a display name."""
    code = normalize_language_code(raw)
    return LANGUAGE_CODE_TO_NAME.get(code, raw.strip())


def miles_to_km(miles: float) -> float:
    """Convert miles to kilometres rounded to 2 decimal places."""
    return round(miles * 1.60934, 2)


def metres_to_km(metres: float) -> float:
    """Convert metres to kilometres rounded to 2 decimal places."""
    return round(metres / 1000.0, 2)


def extract_numeric_hints(query: str) -> dict[str, float | None]:
    """Extract unambiguous numeric radius and budget hints from raw text."""
    radius_km: float | None = None
    if m := _KM_RE.search(query):
        radius_km = round(float(m.group(1)), 2)
    elif m := _MILES_RE.search(query):
        radius_km = miles_to_km(float(m.group(1)))
    elif m := _METRES_RE.search(query):
        radius_km = metres_to_km(float(m.group(1)))

    budget_exact: float | None = None
    budget_max: float | None = None
    if m := _EXACT_BUDGET_RE.search(query):
        budget_exact = float(m.group(1).replace(",", ""))
        budget_max = budget_exact
    elif m := _BUDGET_MAX_RE.search(query):
        budget_max = float(m.group(1).replace(",", ""))

    return {
        "radius_km": radius_km,
        "budget_max": budget_max,
        "budget_exact": budget_exact,
    }


def normalize_preferences(
    prefs: SearchPreferences, raw_query: str = ""
) -> SearchPreferences:
    """Apply deterministic normalization and consistency checks to parsed preferences."""
    specialty = normalize_specialty(prefs.specialty)
    languages = [normalize_language_name(lang) for lang in prefs.languages]
    # Deduplicate preserving order
    languages = list(dict.fromkeys(languages))

    hints = extract_numeric_hints(raw_query) if raw_query else {}
    radius_km = (
        prefs.radius_km if prefs.radius_km is not None else hints.get("radius_km")
    )
    budget_exact = (
        prefs.budget_exact
        if prefs.budget_exact is not None
        else hints.get("budget_exact")
    )
    budget_max = (
        prefs.budget_max if prefs.budget_max is not None else hints.get("budget_max")
    )

    hard_constraints = list(prefs.hard_constraints)
    verification_required = prefs.verification_required or any(
        c.lower() == "verification:verified" for c in hard_constraints
    )
    if verification_required and "verification:verified" not in hard_constraints:
        hard_constraints.append("verification:verified")

    for constraint in hard_constraints:
        if constraint.lower().startswith("budget_exact:") and budget_exact is None:
            try:
                budget_exact = float(constraint.split(":", 1)[1])
                if budget_max is None:
                    budget_max = budget_exact
            except ValueError:
                pass

    return SearchPreferences(
        specialty=specialty,
        languages=languages,
        language_mode=prefs.language_mode,
        location=prefs.location,
        radius_km=radius_km,
        budget_max=budget_max,
        budget_exact=budget_exact,
        min_experience_years=prefs.min_experience_years,
        availability=prefs.availability,
        verification_required=verification_required,
        hard_constraints=hard_constraints,
        preferences=prefs.preferences,
        ranking_profile=prefs.ranking_profile,
        needs_clarification=prefs.needs_clarification,
        clarification_reason=prefs.clarification_reason,
        unanswerable=prefs.unanswerable,
        unanswerable_reason=prefs.unanswerable_reason,
    )
