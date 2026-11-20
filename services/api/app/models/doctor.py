from __future__ import annotations
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.provider import Provider
    from app.models.specialty import Specialty
    from app.models.language import DoctorLanguage


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    qualifications: Mapped[str | None] = mapped_column(Text)
    specialty_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("specialties.id", ondelete="SET NULL")
    )
    is_dummy: Mapped[bool] = mapped_column(Boolean, default=True)

    provider: Mapped[Provider] = relationship("Provider", back_populates="doctors")
    specialty: Mapped[Specialty | None] = relationship("Specialty", back_populates="doctors")
    doctor_languages: Mapped[list[DoctorLanguage]] = relationship(
        "DoctorLanguage", back_populates="doctor", cascade="all, delete-orphan"
    )
