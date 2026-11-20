"""Initial schema with PostGIS, all tables and indexes.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
import geoalchemy2
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")

    # Enums
    provider_type = postgresql.ENUM(
        "clinic", "hospital", "independent_doctor", name="provider_type"
    )
    provider_type.create(op.get_bind(), checkfirst=True)

    verification_status = postgresql.ENUM(
        "verified", "pending", "rejected", name="verification_status"
    )
    verification_status.create(op.get_bind(), checkfirst=True)

    language_proficiency = postgresql.ENUM(
        "basic", "fluent", "native", name="language_proficiency"
    )
    language_proficiency.create(op.get_bind(), checkfirst=True)

    review_status = postgresql.ENUM(
        "pending", "approved", "hidden", name="review_status"
    )
    review_status.create(op.get_bind(), checkfirst=True)

    # specialties
    op.create_table(
        "specialties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
    )

    # languages
    op.create_table(
        "languages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(10), nullable=False, unique=True),
        sa.Column("name", sa.String(50), nullable=False),
    )

    # providers
    op.create_table(
        "providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.Enum("clinic", "hospital", "independent_doctor", name="provider_type"), nullable=False),
        sa.Column("address", sa.Text, nullable=False),
        sa.Column("city", sa.String(100), nullable=False, server_default="Goa"),
        sa.Column(
            "location",
            geoalchemy2.types.Geography(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.Column("phone", sa.String(30)),
        sa.Column("whatsapp", sa.String(30)),
        sa.Column("opening_hours", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("registration_number", sa.String(100)),
        sa.Column(
            "verification_status",
            sa.Enum("verified", "pending", "rejected", name="verification_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("walk_in_available", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_dummy", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # GiST index on provider location
    op.create_index(
        "ix_providers_location",
        "providers",
        ["location"],
        postgresql_using="gist",
    )
    op.create_index("ix_providers_verification_status", "providers", ["verification_status"])
    op.create_index("ix_providers_is_dummy", "providers", ["is_dummy"])

    # doctors
    op.create_table(
        "doctors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("qualifications", sa.Text),
        sa.Column("specialty_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("specialties.id", ondelete="SET NULL")),
        sa.Column("is_dummy", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_doctors_provider_id", "doctors", ["provider_id"])
    op.create_index("ix_doctors_specialty_id", "doctors", ["specialty_id"])

    # doctor_languages
    op.create_table(
        "doctor_languages",
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("doctors.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("language_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "proficiency",
            sa.Enum("basic", "fluent", "native", name="language_proficiency"),
            nullable=False,
            server_default="fluent",
        ),
    )
    op.create_index("ix_doctor_languages_language_id", "doctor_languages", ["language_id"])

    # services
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("price_min", sa.Numeric(10, 2)),
        sa.Column("price_max", sa.Numeric(10, 2)),
        sa.Column("currency", sa.String(10), server_default="INR"),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_services_provider_id", "services", ["provider_id"])

    # search_requests
    op.create_table(
        "search_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lng", sa.Float, nullable=False),
        sa.Column("language_code", sa.String(10), nullable=False),
        sa.Column("need_category", sa.String(50), nullable=False),
        sa.Column("results_count", sa.Integer, server_default="0"),
        sa.Column("session_id", sa.String(100)),
    )
    op.create_index("ix_search_requests_created_at", "search_requests", ["created_at"])
    op.create_index("ix_search_requests_language_code", "search_requests", ["language_code"])

    # reviews
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("search_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("search_requests.id", ondelete="SET NULL")),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("actual_amount_paid", sa.Numeric(10, 2)),
        sa.Column("currency", sa.String(10), server_default="INR"),
        sa.Column("comment", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "hidden", name="review_status"),
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_index("ix_reviews_provider_id", "reviews", ["provider_id"])
    op.create_index("ix_reviews_status", "reviews", ["status"])

    # analytics_events
    op.create_table(
        "analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(100), nullable=False),
        sa.Column("event_name", sa.String(100), nullable=False),
        sa.Column("properties", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_analytics_events_session_id", "analytics_events", ["session_id"])
    op.create_index("ix_analytics_events_event_name", "analytics_events", ["event_name"])
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("analytics_events")
    op.drop_table("reviews")
    op.drop_table("search_requests")
    op.drop_table("services")
    op.drop_table("doctor_languages")
    op.drop_table("doctors")
    op.drop_table("providers")
    op.drop_table("languages")
    op.drop_table("specialties")

    op.execute("DROP TYPE IF EXISTS review_status")
    op.execute("DROP TYPE IF EXISTS language_proficiency")
    op.execute("DROP TYPE IF EXISTS verification_status")
    op.execute("DROP TYPE IF EXISTS provider_type")
