"""POST /search — matching engine endpoint."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

try:
    from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_GeogFromText
except ImportError:
    def ST_DWithin(*args): return True
    def ST_Distance(*args): return 0
    def ST_GeogFromText(*args): return ""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.matching.engine import (
    build_match_reasons,
    compute_score,
    get_max_radius_km,
)
from app.models.doctor import Doctor
from app.models.language import DoctorLanguage, Language
from app.models.provider import Provider
from app.models.review import Review
from app.models.search_request import SearchRequest
from app.models.service import Service
from app.schemas import ProviderSummary, SearchResponse
from app.schemas import SearchRequest as SearchRequestSchema

router = APIRouter(tags=["search"])

VALID_NEED_CATEGORIES = [
    "fever", "stomach_issue", "injury", "dental_pain",
    "skin_problem", "ear_nose_throat", "child_health", "other",
]


@router.post("/search", response_model=SearchResponse)
async def search_providers(
    body: SearchRequestSchema,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    if body.need_category not in VALID_NEED_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid need_category. Must be one of: {VALID_NEED_CATEGORIES}",
        )

    max_radius_km = get_max_radius_km()
    # Convert km to metres for ST_DWithin (geography type uses metres)
    max_radius_m = max_radius_km * 1000

    user_point = f"SRID=4326;POINT({body.lng} {body.lat})"

    # --- Fetch providers within radius (excluding rejected) ---
    stmt = (
        select(
            Provider,
            ST_Distance(Provider.location, ST_GeogFromText(user_point)).label(
                "distance_m"
            ),
        )
        .where(
            Provider.verification_status != "rejected",
            ST_DWithin(Provider.location, ST_GeogFromText(user_point), max_radius_m),
        )
        .options(
            selectinload(Provider.doctors).selectinload(Doctor.specialty),
            selectinload(Provider.doctors).selectinload(Doctor.doctor_languages).selectinload(DoctorLanguage.language),
            selectinload(Provider.services),
        )
        .order_by("distance_m")
        .limit(50)  # Fetch more than 10 so scoring can reorder
    )

    result = await db.execute(stmt)
    rows = result.all()

    # --- Fetch avg ratings ---
    prov_ids = [r.Provider.id for r in rows]
    if prov_ids:
        rating_stmt = (
            select(
                Review.provider_id,
                func.avg(Review.rating).label("avg_rating"),
                func.count(Review.id).label("review_count"),
            )
            .where(
                Review.provider_id.in_(prov_ids),
                Review.status == "approved",
            )
            .group_by(Review.provider_id)
        )
        rating_result = await db.execute(rating_stmt)
        ratings_map = {
            str(r.provider_id): (float(r.avg_rating), int(r.review_count))
            for r in rating_result.all()
        }
    else:
        ratings_map = {}

    # --- Fetch language names for match_reasons ---
    lang_result = await db.execute(select(Language))
    language_names = {
        lang.code.lower(): lang.name for lang in lang_result.scalars().all()
    }

    # --- Score each provider ---
    scored: list[tuple[float, ProviderSummary]] = []

    for row in rows:
        provider: Provider = row.Provider
        distance_m: float = row.distance_m
        distance_km = round(distance_m / 1000.0, 2)

        # Collect language codes from all doctors
        lang_codes: list[str] = []
        for doc in provider.doctors:
            for dl in doc.doctor_languages:
                if dl.language and dl.language.code not in lang_codes:
                    lang_codes.append(dl.language.code.lower())

        # Collect specialty slugs
        specialty_slugs = [
            doc.specialty.slug for doc in provider.doctors if doc.specialty
        ]

        # Ratings
        rating_data = ratings_map.get(str(provider.id))
        avg_rating = rating_data[0] if rating_data else None
        review_count = rating_data[1] if rating_data else 0

        # Score
        score, sub_scores = compute_score(
            distance_km=distance_km,
            language_codes=lang_codes,
            requested_language=body.language_code,
            opening_hours=provider.opening_hours,
            timezone_str=provider.timezone,
            walk_in_available=provider.walk_in_available,
            specialty_slugs=specialty_slugs,
            need_category=body.need_category,
            verification_status=provider.verification_status,
            average_rating=avg_rating,
            max_radius_km=max_radius_km,
        )

        # Build price range for the matched need
        price_range = _get_price_range(provider.services, body.need_category)

        # Match reasons
        reasons = build_match_reasons(
            sub_scores=sub_scores,
            distance_km=distance_km,
            requested_language=body.language_code,
            language_names=language_names,
            need_category=body.need_category,
        )

        # Is open now?
        is_open = sub_scores["open_now"] == 1.0

        lat, lng = extract_lat_lng(provider.location)

        summary = ProviderSummary(
            id=provider.id,
            name=provider.name,
            type=provider.type,
            address=provider.address,
            distance_km=distance_km,
            score=score,
            is_open_now=is_open,
            walk_in_available=provider.walk_in_available,
            verification_status=provider.verification_status,
            languages=lang_codes,
            language_names=[language_names.get(c, c) for c in lang_codes],
            price_range=price_range,
            average_rating=round(avg_rating, 1) if avg_rating else None,
            review_count=review_count,
            match_reasons=reasons,
            lat=lat,
            lng=lng,
        )
        scored.append((score, summary))

    # Sort descending by score, return top 10
    scored.sort(key=lambda x: x[0], reverse=True)
    top_results = [s for _, s in scored[:10]]

    # --- Log search request ---
    search_req = SearchRequest(
        id=uuid.uuid4(),
        lat=body.lat,
        lng=body.lng,
        language_code=body.language_code,
        need_category=body.need_category,
        results_count=len(top_results),
        session_id=body.session_id,
    )
    db.add(search_req)
    await db.commit()
    await db.refresh(search_req)

    return SearchResponse(
        search_request_id=search_req.id,
        results=top_results,
        total=len(top_results),
    )


SERVICE_TO_NEED: dict[str, list[str]] = {
    "general_consultation": [
        "fever",
        "stomach_issue",
        "skin_problem",
        "ear_nose_throat",
        "child_health",
        "other",
    ],
    "fever_treatment": ["fever"],
    "stomach_issue_treatment": ["stomach_issue"],
    "stitches": ["injury"],
    "minor_injury_dressing": ["injury"],
    "xray": ["injury", "orthopedic"],
    "dental_checkup": ["dental_pain"],
    "basic_blood_test": ["fever", "stomach_issue"],
    "emergency_care": ["injury"],
}


def _get_price_range(services: list[Service], need_category: str) -> str | None:
    """Find the most relevant service price for the given need."""
    # Try to find a need-specific service first
    for need_key, service_names in SERVICE_TO_NEED.items():
        if need_category in service_names:
            for svc in services:
                if svc.name == need_key and svc.price_min and svc.price_max:
                    return f"₹{int(svc.price_min)}–₹{int(svc.price_max)}"

    # Fallback: general consultation
    for svc in services:
        if svc.name == "general_consultation" and svc.price_min and svc.price_max:
            return f"₹{int(svc.price_min)}–₹{int(svc.price_max)}"

    # Any service
    for svc in services:
        if svc.price_min and svc.price_max:
            return f"₹{int(svc.price_min)}–₹{int(svc.price_max)}"

    return None


def extract_lat_lng(location: object) -> tuple[float, float]:
    """Extract (lat, lng) from a PostGIS WKBElement without requiring shapely."""
    if location is None:
        return 0.0, 0.0
    try:
        from geoalchemy2.shape import to_shape
        point = to_shape(location)
        return float(point.y), float(point.x)
    except Exception:
        pass
    try:
        import struct
        raw = bytes(getattr(location, "data", location))
        endian = "<" if raw[0] == 1 else ">"
        geom_type = struct.unpack(f"{endian}I", raw[1:5])[0]
        offset = 9 if (geom_type & 0x20000000) else 5
        lng, lat = struct.unpack(f"{endian}dd", raw[offset : offset + 16])
        return float(lat), float(lng)
    except Exception:
        return 0.0, 0.0

