from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

try:
    from geoalchemy2 import Geography
except ImportError:
    from sqlalchemy.types import UserDefinedType
    class Geography(UserDefinedType):
        def __init__(self, *args, **kwargs):
            pass
        def get_col_spec(self, **kw):
            return "GEOGRAPHY"

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.doctor import Doctor
    from app.models.service import Service
    from app.models.review import Review


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(
        Enum("clinic", "hospital", "independent_doctor", name="provider_type"),
        nullable=False,
    )
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Goa")
    location: Mapped[object] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=False
    )
    phone: Mapped[str | None] = mapped_column(String(30))
    whatsapp: Mapped[str | None] = mapped_column(String(30))
    # JSONB structure: {"24x7": true} OR {"mon": [{"open": "09:00", "close": "18:00"}], ...}
    opening_hours: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Asia/Kolkata"
    )
    registration_number: Mapped[str | None] = mapped_column(String(100))
    verification_status: Mapped[str] = mapped_column(
        Enum("verified", "pending", "rejected", name="verification_status"),
        nullable=False,
        default="pending",
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    walk_in_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_dummy: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    doctors: Mapped[list[Doctor]] = relationship(
        "Doctor", back_populates="provider", cascade="all, delete-orphan"
    )
    services: Mapped[list[Service]] = relationship(
        "Service", back_populates="provider", cascade="all, delete-orphan"
    )
    reviews: Mapped[list[Review]] = relationship(
        "Review", back_populates="provider"
    )
