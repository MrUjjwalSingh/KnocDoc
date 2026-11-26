"""GET /providers/{id} — full provider profile."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.doctor import Doctor
from app.models.language import DoctorLanguage
from app.models.provider import Provider
from app.models.review import Review
from app.schemas import DoctorOut, ProviderDetail, ServiceOut

router = APIRouter(tags=["providers"])


@router.get("/providers/{provider_id}", response_model=ProviderDetail)
async def get_provider(
    provider_id: uuid.UUID = Path(..., description="Provider UUID"),
    db: AsyncSession = Depends(get_db),
) -> ProviderDetail:
    stmt = (
        select(Provider)
        .where(Provider.id == provider_id)
        .options(
            selectinload(Provider.doctors).selectinload(Doctor.specialty),
            selectinload(Provider.doctors).selectinload(Doctor.doctor_languages).selectinload(DoctorLanguage.language),
            selectinload(Provider.services),
        )
    )
    result = await db.execute(stmt)
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Fetch ratings
    rating_stmt = (
        select(
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("review_count"),
        )
        .where(
            Review.provider_id == provider.id,
            Review.status == "approved",
        )
    )
    rating_res = await db.execute(rating_stmt)
    rating_row = rating_res.one_or_none()
    avg_rating = (
        float(rating_row.avg_rating)
        if rating_row and rating_row.avg_rating
        else None
    )
    review_count = (
        int(rating_row.review_count)
        if rating_row and rating_row.review_count
        else 0
    )

    # Extract coordinates
    from app.routers.search import extract_lat_lng
    lat, lng = extract_lat_lng(provider.location)

    doctors_out = [DoctorOut.from_orm_with_languages(doc) for doc in provider.doctors]
    services_out = [ServiceOut.model_validate(s) for s in provider.services]

    return ProviderDetail(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        address=provider.address,
        city=provider.city,
        phone=provider.phone,
        whatsapp=provider.whatsapp,
        opening_hours=provider.opening_hours,
        timezone=provider.timezone,
        verification_status=provider.verification_status,
        last_verified_at=provider.last_verified_at,
        walk_in_available=provider.walk_in_available,
        is_dummy=provider.is_dummy,
        average_rating=round(avg_rating, 1) if avg_rating else None,
        review_count=review_count,
        doctors=doctors_out,
        services=services_out,
        lat=lat,
        lng=lng,
    )

