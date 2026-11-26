"""Search orchestration service for structured and natural-language queries."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pytz
from fastapi import HTTPException
from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

try:
    from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_GeogFromText
except ImportError:

    def ST_DWithin(*args: Any) -> Any:
        return literal(True)

    def ST_Distance(*args: Any) -> Any:
        return literal(0)

    def ST_GeogFromText(*args: Any) -> str:
        return ""


from app.matching.engine import (
    build_match_reasons,
    compute_open_now_score,
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
from app.search.normalizer import normalize_language_code
from app.search.query_parser import QueryParserError, parse_search_query
from app.search.schemas import SearchPreferences

VALID_NEED_CATEGORIES = [
    "fever",
    "stomach_issue",
    "injury",
    "dental_pain",
    "skin_problem",
    "ear_nose_throat",
    "child_health",
    "other",
]

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


def get_price_range(services: list[Service], need_category: str) -> str | None:
    """Find the most relevant service price range for display."""
    for svc_name, need_keys in SERVICE_TO_NEED.items():
        if need_category in need_keys:
            for svc in services:
                if (
                    svc.name == svc_name
                    and svc.price_min is not None
                    and svc.price_max is not None
                ):
                    return f"₹{int(svc.price_min)}–₹{int(svc.price_max)}"

    for svc in services:
        if (
            svc.name == "general_consultation"
            and svc.price_min is not None
            and svc.price_max is not None
        ):
            return f"₹{int(svc.price_min)}–₹{int(svc.price_max)}"

    for svc in services:
        if svc.price_min is not None and svc.price_max is not None:
            return f"₹{int(svc.price_min)}–₹{int(svc.price_max)}"

    return None


def get_min_consultation_price(services: list[Service]) -> float | None:
    """Return the lowest known consultation fee for a provider."""
    for svc in services:
        if svc.name == "general_consultation" and svc.price_min is not None:
            return float(svc.price_min)
    prices = [float(svc.price_min) for svc in services if svc.price_min is not None]
    return min(prices) if prices else None


def _is_open_today(
    opening_hours: dict, timezone_str: str, now: datetime | None = None
) -> bool:
    if not opening_hours:
        return False
    if opening_hours.get("24x7"):
        return True
    try:
        tz = pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        tz = pytz.UTC
    current = now.astimezone(tz) if now and now.tzinfo else datetime.now(tz)
    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    slots = opening_hours.get(day_names[current.weekday()], [])
    return bool(slots)


def detect_unsupported_constraints(prefs: SearchPreferences) -> list[str]:
    """Identify hard constraints that cannot be verified with the current database schema."""
    unsupported: list[str] = []
    for constraint in prefs.hard_constraints:
        lower = constraint.lower()
        if lower.startswith("min_experience_years:"):
            unsupported.append(
                "Minimum years of doctor experience is not recorded in the current directory schema."
            )
        elif lower.startswith("availability:tomorrow_"):
            unsupported.append(
                "Specific future appointment time slots (e.g., tomorrow at a set time) are not supported."
            )
        elif lower.startswith("verified_reviews_min:") or lower.startswith(
            "rating_exact:"
        ):
            unsupported.append(
                "Exact rating or minimum review-count thresholds cannot be guaranteed."
            )
        elif lower.startswith("credential:"):
            unsupported.append(
                "Specific board-certification credentials beyond provider verification are not indexed."
            )

    if prefs.availability.startswith("tomorrow_") and not any(
        "appointment" in msg for msg in unsupported
    ):
        unsupported.append(
            "Specific future appointment time slots (e.g., tomorrow at a set time) are not supported."
        )
    return unsupported


def passes_hard_constraints(
    *,
    specialty_slugs: list[str],
    language_codes: list[str],
    services: list[Service],
    opening_hours: dict,
    timezone_str: str,
    walk_in_available: bool,
    verification_status: str,
    prefs: SearchPreferences,
) -> tuple[bool, list[str]]:
    """
    Evaluate all supported hard constraints for a candidate provider.
    Returns (passes, reasons_failed).
    """
    failed: list[str] = []

    # 1. Verification
    if prefs.verification_required and verification_status != "verified":
        failed.append("verification:verified")

    # 2. Specialty
    if prefs.specialty:
        slugs_lower = {s.lower() for s in specialty_slugs}
        if prefs.specialty.lower() not in slugs_lower:
            failed.append(f"specialty:{prefs.specialty}")

    # 3. Languages
    if prefs.languages:
        req_codes = [normalize_language_code(lang) for lang in prefs.languages]
        prov_codes = {c.lower() for c in language_codes}
        if prefs.language_mode == "all":
            if not all(code in prov_codes for code in req_codes):
                failed.append(f"languages_all:{','.join(prefs.languages)}")
        else:
            if not any(code in prov_codes for code in req_codes):
                failed.append(f"language_any:{'|'.join(prefs.languages)}")

    # 4. Budget
    min_price = get_min_consultation_price(services)
    if prefs.budget_exact is not None:
        exact_match = any(
            svc.price_min is not None
            and svc.price_max is not None
            and float(svc.price_min) <= prefs.budget_exact <= float(svc.price_max)
            for svc in services
        )
        if not exact_match:
            failed.append(f"budget_exact:{int(prefs.budget_exact)}")
    elif prefs.budget_max is not None:
        if min_price is None or min_price > prefs.budget_max:
            failed.append(f"budget_max:{int(prefs.budget_max)}")

    # 5. Availability
    avail = prefs.availability
    if avail == "open_now":
        if (
            compute_open_now_score(opening_hours, timezone_str, walk_in_available)
            != 1.0
        ):
            failed.append("availability:open_now")
    elif avail == "open_24_7":
        if not opening_hours.get("24x7"):
            failed.append("availability:open_24_7")
    elif avail == "open_today":
        if not _is_open_today(opening_hours, timezone_str):
            failed.append("availability:open_today")

    return len(failed) == 0, failed


async def execute_search(
    body: SearchRequestSchema,
    db: AsyncSession,
) -> SearchResponse:
    """Orchestrate structured or natural-language provider search."""
    prefs: SearchPreferences | None = None

    if body.query and body.query.strip():
        try:
            prefs = await parse_search_query(body.query)
        except QueryParserError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail={"error": exc.code, "message": exc.message},
            ) from exc

        if prefs.unanswerable:
            return SearchResponse(
                search_request_id=uuid.uuid4(),
                results=[],
                total=0,
                parsed_preferences=prefs.model_dump(),
                applied_profile=prefs.ranking_profile,
                unanswerable=True,
                unanswerable_message=(
                    prefs.unanswerable_reason
                    or "This query cannot be answered by the KnocDoc provider directory."
                ),
            )

        if prefs.needs_clarification or body.lat is None or body.lng is None:
            return SearchResponse(
                search_request_id=uuid.uuid4(),
                results=[],
                total=0,
                parsed_preferences=prefs.model_dump(),
                applied_profile=prefs.ranking_profile,
                clarification_needed=True,
                clarification_message=(
                    prefs.clarification_reason
                    or "Please share your current location or select a city area to search nearby doctors."
                ),
            )

        unsupported = detect_unsupported_constraints(prefs)
        if unsupported:
            return SearchResponse(
                search_request_id=uuid.uuid4(),
                results=[],
                total=0,
                parsed_preferences=prefs.model_dump(),
                applied_profile=prefs.ranking_profile,
                limiting_constraints=unsupported,
                unsupported_constraints=unsupported,
            )
    else:
        if body.lat is None or body.lng is None:
            raise HTTPException(
                status_code=422,
                detail="lat and lng are required when query is not provided.",
            )
        if body.need_category not in VALID_NEED_CATEGORIES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid need_category. Must be one of: {VALID_NEED_CATEGORIES}",
            )

    lat = float(body.lat)  # type: ignore[arg-type]
    lng = float(body.lng)  # type: ignore[arg-type]

    default_max_radius = get_max_radius_km()
    effective_radius_km = (
        prefs.radius_km
        if (prefs and prefs.radius_km is not None)
        else default_max_radius
    )
    effective_radius_m = effective_radius_km * 1000.0
    user_point = f"SRID=4326;POINT({lng} {lat})"

    where_clauses = [
        Provider.verification_status != "rejected",
        ST_DWithin(Provider.location, ST_GeogFromText(user_point), effective_radius_m),
    ]
    if prefs and prefs.verification_required:
        where_clauses.append(Provider.verification_status == "verified")

    stmt = (
        select(
            Provider,
            ST_Distance(Provider.location, ST_GeogFromText(user_point)).label(
                "distance_m"
            ),
        )
        .where(*where_clauses)
        .options(
            selectinload(Provider.doctors).selectinload(Doctor.specialty),
            selectinload(Provider.doctors)
            .selectinload(Doctor.doctor_languages)
            .selectinload(DoctorLanguage.language),
            selectinload(Provider.services),
        )
        .order_by("distance_m")
        .limit(100)
    )

    result = await db.execute(stmt)
    rows = result.all()

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

    lang_result = await db.execute(select(Language))
    language_names = {
        lang.code.lower(): lang.name for lang in lang_result.scalars().all()
    }

    scored: list[tuple[float, float, str, ProviderSummary]] = []
    failure_counts: dict[str, int] = {}

    for row in rows:
        provider: Provider = row.Provider
        distance_km = round(float(row.distance_m) / 1000.0, 2)

        lang_codes: list[str] = []
        for doc in provider.doctors:
            for dl in doc.doctor_languages:
                if dl.language and dl.language.code.lower() not in lang_codes:
                    lang_codes.append(dl.language.code.lower())

        specialty_slugs = [
            doc.specialty.slug for doc in provider.doctors if doc.specialty
        ]

        if prefs is not None:
            ok, failed_reasons = passes_hard_constraints(
                specialty_slugs=specialty_slugs,
                language_codes=lang_codes,
                services=provider.services,
                opening_hours=provider.opening_hours,
                timezone_str=provider.timezone,
                walk_in_available=provider.walk_in_available,
                verification_status=provider.verification_status,
                prefs=prefs,
            )
            if not ok:
                for reason in failed_reasons:
                    failure_counts[reason] = failure_counts.get(reason, 0) + 1
                continue

        rating_data = ratings_map.get(str(provider.id))
        avg_rating = rating_data[0] if rating_data else None
        review_count = rating_data[1] if rating_data else 0
        min_price = get_min_consultation_price(provider.services)

        req_lang_codes = (
            [normalize_language_code(lang) for lang in prefs.languages]
            if prefs and prefs.languages
            else None
        )

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
            max_radius_km=effective_radius_km,
            profile=prefs.ranking_profile if prefs else None,
            requested_languages=req_lang_codes,
            language_mode=prefs.language_mode if prefs else "any",
            requested_specialty=prefs.specialty if prefs else None,
            min_price=min_price,
            budget_max=prefs.budget_max if prefs else None,
        )

        price_range = get_price_range(provider.services, body.need_category)
        reasons = build_match_reasons(
            sub_scores=sub_scores,
            distance_km=distance_km,
            requested_language=body.language_code,
            language_names=language_names,
            need_category=body.need_category,
            requested_languages=req_lang_codes,
            provider_language_codes=lang_codes,
            requested_specialty=prefs.specialty if prefs else None,
            min_price=min_price,
            budget_max=prefs.budget_max if prefs else None,
            profile=prefs.ranking_profile if prefs else None,
        )

        prov_lat, prov_lng = extract_lat_lng(provider.location)
        summary = ProviderSummary(
            id=provider.id,
            name=provider.name,
            type=provider.type,
            address=provider.address,
            distance_km=distance_km,
            score=score,
            is_open_now=sub_scores["open_now"] == 1.0,
            walk_in_available=provider.walk_in_available,
            verification_status=provider.verification_status,
            languages=lang_codes,
            language_names=[language_names.get(c, c) for c in lang_codes],
            price_range=price_range,
            average_rating=round(avg_rating, 1) if avg_rating else None,
            review_count=review_count,
            match_reasons=reasons,
            lat=prov_lat,
            lng=prov_lng,
        )
        scored.append((-score, distance_km, str(provider.id), summary))

    scored.sort(key=lambda item: (item[0], item[1], item[2]))
    top_results = [item[3] for item in scored[:10]]

    limiting: list[str] = []
    if not top_results:
        if not rows:
            limiting.append(f"No providers found within {effective_radius_km:.1f} km")
        else:
            limiting.extend(sorted(failure_counts.keys()))

    effective_lang = (
        normalize_language_code(prefs.languages[0])[:10]
        if prefs and prefs.languages
        else body.language_code
    )
    effective_need = (
        prefs.specialty[:50] if prefs and prefs.specialty else body.need_category
    )

    search_req = SearchRequest(
        id=uuid.uuid4(),
        lat=lat,
        lng=lng,
        language_code=effective_lang,
        need_category=effective_need,
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
        parsed_preferences=prefs.model_dump() if prefs else None,
        applied_profile=prefs.ranking_profile if prefs else "balanced",
        limiting_constraints=limiting,
    )
