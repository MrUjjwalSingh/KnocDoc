"""POST /events — analytics event ingestion."""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.analytics import AnalyticsEvent
from app.schemas import EventCreate

router = APIRouter(tags=["analytics"])

ALLOWED_EVENTS = {
    "search_submitted",
    "results_viewed",
    "provider_opened",
    "call_tapped",
    "whatsapp_tapped",
    "directions_tapped",
    "feedback_submitted",
}


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def log_event(
    body: EventCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    # Record event
    event = AnalyticsEvent(
        id=uuid.uuid4(),
        session_id=body.session_id,
        event_name=body.event_name,
        properties=body.properties,
    )
    db.add(event)
    await db.commit()

    return {"status": "accepted"}

