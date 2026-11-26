"""Pydantic v2 schemas for LLM-parsed natural-language search preferences."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_AVAILABILITY = {
    "open_now",
    "open_today",
    "open_24_7",
    "open_24_7_preferred",
    "unspecified",
}
_TOMORROW_TIME_RE = re.compile(r"^tomorrow_\d{2}:\d{2}$")

PreferenceName = Literal[
    "distance",
    "cost",
    "language",
    "experience",
    "rating",
    "verification",
    "availability",
]

RankingProfileName = Literal[
    "balanced",
    "nearest",
    "budget_focused",
    "experience_focused",
]


class SearchPreferences(BaseModel):
    """Validated structured representation of a natural-language doctor search query."""

    model_config = ConfigDict(extra="forbid")

    specialty: str | None = None
    languages: list[str] = Field(default_factory=list)
    language_mode: Literal["any", "all"] = "any"

    location: str | None = None
    radius_km: float | None = Field(default=None, ge=0.0, le=500.0)

    budget_max: float | None = Field(default=None, ge=0.0)
    budget_exact: float | None = Field(default=None, ge=0.0)
    min_experience_years: float | None = Field(default=None, ge=0.0, le=80.0)

    availability: str = "unspecified"
    verification_required: bool = False

    hard_constraints: list[str] = Field(default_factory=list)
    preferences: list[PreferenceName] = Field(default_factory=list)
    ranking_profile: RankingProfileName = "balanced"

    needs_clarification: bool = False
    clarification_reason: str | None = None
    unanswerable: bool = False
    unanswerable_reason: str | None = None

    @field_validator(
        "specialty",
        "location",
        "clarification_reason",
        "unanswerable_reason",
        mode="before",
    )
    @classmethod
    def _strip_empty_strings(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return value

    @field_validator("availability", mode="before")
    @classmethod
    def _validate_availability(cls, value: object) -> str:
        if value is None or value == "":
            return "unspecified"
        if not isinstance(value, str):
            raise ValueError("availability must be a string")
        cleaned = value.strip().lower()
        if cleaned in ALLOWED_AVAILABILITY or _TOMORROW_TIME_RE.match(cleaned):
            return cleaned
        raise ValueError(
            f"Unsupported availability value '{value}'. "
            f"Allowed: {sorted(ALLOWED_AVAILABILITY)} or 'tomorrow_HH:MM'."
        )

    @field_validator("languages", "hard_constraints", mode="before")
    @classmethod
    def _ensure_string_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("Expected a list of strings")
        result: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("List items must be strings")
            cleaned = item.strip()
            if cleaned and cleaned not in result:
                result.append(cleaned)
        return result

    @field_validator("preferences", mode="before")
    @classmethod
    def _dedupe_preferences(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        seen: list[str] = []
        for item in value:
            if isinstance(item, str):
                norm = item.strip().lower()
                if norm and norm not in seen:
                    seen.append(norm)
        return seen
