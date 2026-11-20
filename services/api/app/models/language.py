from __future__ import annotations
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.doctor import Doctor


class Language(Base):
    __tablename__ = "languages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    doctor_languages: Mapped[list[DoctorLanguage]] = relationship(
        "DoctorLanguage", back_populates="language"
    )


class DoctorLanguage(Base):
    __tablename__ = "doctor_languages"

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE"), primary_key=True
    )
    language_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True
    )
    proficiency: Mapped[str] = mapped_column(
        Enum("basic", "fluent", "native", name="language_proficiency"),
        nullable=False,
        default="fluent",
    )

    doctor: Mapped[Doctor] = relationship("Doctor", back_populates="doctor_languages")
    language: Mapped[Language] = relationship("Language", back_populates="doctor_languages")
