from __future__ import annotations
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.doctor import Doctor

SPECIALTY_SLUGS = [
    "general_physician",
    "pediatrics",
    "dental",
    "orthopedic",
    "emergency_care",
    "dermatology",
    "gastroenterology",
    "ent",
]


class Specialty(Base):
    __tablename__ = "specialties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    doctors: Mapped[list[Doctor]] = relationship("Doctor", back_populates="specialty")
