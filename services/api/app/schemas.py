"""Pydantic v2 schemas for TravelDoc API."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


# --- Specialty ---
class SpecialtyOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str

    model_config = {"from_attributes": True}


# --- Language ---
class LanguageOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str

    model_config = {"from_attributes": True}


class DoctorLanguageOut(BaseModel):
    language: LanguageOut
    proficiency: str

    model_config = {"from_attributes": True}


# --- Doctor ---
class DoctorOut(BaseModel):
    id: uuid.UUID
    full_name: str
    qualifications: str | None
    specialty: SpecialtyOut | None
    languages: list[DoctorLanguageOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_languages(cls, doctor: Any) -> "DoctorOut":
        return cls(
            id=doctor.id,
            full_name=doctor.full_name,
            qualifications=doctor.qualifications,
            specialty=SpecialtyOut.model_validate(doctor.specialty) if doctor.specialty else None,
            languages=[
                DoctorLanguageOut(
                    language=LanguageOut.model_validate(dl.language),
                    proficiency=dl.proficiency,
                )
                for dl in doctor.doctor_languages
            ],
        )


# --- Service ---
class ServiceOut(BaseModel):
    id: uuid.UUID
    name: str
    price_min: float | None
    price_max: float | None
    currency: str
    last_verified_at: datetime | None

    model_config = {"from_attributes": True}


# --- Provider summary (for search results) ---
class MatchReason(BaseModel):
    text: str
    icon: str = ""


class ProviderSummary(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    address: str
    distance_km: float
    score: float
    is_open_now: bool
    walk_in_available: bool
    verification_status: str
    languages: list[str]  # language codes
    language_names: list[str]
    price_range: str | None  # e.g. "₹300–₹800"
    average_rating: float | None
    review_count: int
    match_reasons: list[str]
    lat: float
    lng: float


# --- Provider full profile ---
class ProviderDetail(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    address: str
    city: str
    phone: str | None
    whatsapp: str | None
    opening_hours: dict
    timezone: str
    verification_status: str
    last_verified_at: datetime | None
    walk_in_available: bool
    is_dummy: bool
    average_rating: float | None
    review_count: int
    doctors: list[DoctorOut]
    services: list[ServiceOut]
    lat: float
    lng: float


# --- Search ---
class SearchRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    language_code: str = Field(..., min_length=2, max_length=10)
    need_category: str = Field(...)
    session_id: str | None = None


class SearchResponse(BaseModel):
    search_request_id: uuid.UUID
    results: list[ProviderSummary]
    total: int


# --- Reviews ---
class ReviewCreate(BaseModel):
    provider_id: uuid.UUID
    search_request_id: uuid.UUID | None = None
    rating: int = Field(..., ge=1, le=5)
    actual_amount_paid: float | None = Field(None, ge=0)
    currency: str = "INR"
    comment: str | None = Field(None, max_length=1000)
    session_id: str | None = None


class ReviewOut(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    rating: int
    comment: str | None
    created_at: datetime
    status: str

    model_config = {"from_attributes": True}


# --- Analytics ---
class EventCreate(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    event_name: str = Field(..., min_length=1, max_length=100)
    properties: dict = Field(default_factory=dict)


# --- Config ---
class AppConfig(BaseModel):
    city_name: str
    city_center_lat: float
    city_center_lng: float
    city_currency: str
    city_emergency_number: str
    is_demo_data: bool
    supported_languages: list[dict]
    need_categories: list[dict]


# --- Health ---
class HealthResponse(BaseModel):
    status: str
    version: str

