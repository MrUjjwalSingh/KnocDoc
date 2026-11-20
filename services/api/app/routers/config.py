"""GET /config — city config and supported languages/needs."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.language import Language
from app.schemas import AppConfig

router = APIRouter(tags=["config"])

NEED_CATEGORIES = [
    {"key": "fever", "label": "Fever / Flu", "icon": "🤒"},
    {"key": "stomach_issue", "label": "Stomach Issue", "icon": "🤢"},
    {"key": "injury", "label": "Injury / Wound", "icon": "🩹"},
    {"key": "dental_pain", "label": "Dental Pain", "icon": "🦷"},
    {"key": "skin_problem", "label": "Skin Problem", "icon": "🩺"},
    {"key": "ear_nose_throat", "label": "Ear, Nose & Throat", "icon": "👂"},
    {"key": "child_health", "label": "Child Health", "icon": "👶"},
    {"key": "other", "label": "General / Other", "icon": "➕"},
]


@router.get("/config", response_model=AppConfig)
async def get_config(db: AsyncSession = Depends(get_db)) -> AppConfig:
    settings = get_settings()

    # Fetch languages from DB
    result = await db.execute(select(Language).order_by(Language.name))
    languages = result.scalars().all()

    return AppConfig(
        city_name=settings.city_name,
        city_center_lat=settings.city_center_lat,
        city_center_lng=settings.city_center_lng,
        city_currency=settings.city_currency,
        city_emergency_number=settings.city_emergency_number,
        is_demo_data=settings.is_demo_data,
        supported_languages=[{"code": l.code, "name": l.name} for l in languages],
        need_categories=NEED_CATEGORIES,
    )

