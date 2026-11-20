"""POST /reviews — submit post-visit feedback."""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.provider import Provider
from app.models.review import Review
from app.schemas import ReviewCreate, ReviewOut

router = APIRouter(tags=["reviews"])


@router.post("/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(
    body: ReviewCreate,
    db: AsyncSession = Depends(get_db),
) -> ReviewOut:
    # Check provider exists
    prov = await db.scalar(select(Provider.id).where(Provider.id == body.provider_id))
    if not prov:
        raise HTTPException(status_code=404, detail="Provider not found")

    review = Review(
        id=uuid.uuid4(),
        provider_id=body.provider_id,
        search_request_id=body.search_request_id,
        rating=body.rating,
        actual_amount_paid=body.actual_amount_paid,
        currency=body.currency,
        comment=body.comment,
        status="pending",  # all reviews start pending for moderation
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    return ReviewOut.model_validate(review)

