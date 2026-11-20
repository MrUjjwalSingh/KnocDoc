"""
CSV import script for TravelDoc.

Usage:
    python -m db.import_csv providers.csv
    python -m db.import_csv doctors.csv
    python -m db.import_csv services.csv

See /docs/data-format.md for the expected CSV format.
"""
from __future__ import annotations

import argparse
import csv
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "api"))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Doctor, Language, Provider, Service, Specialty


def get_sync_engine():
    settings = get_settings()
    return create_engine(settings.database_url_sync, echo=False)


def import_providers(filepath: Path, session: Session) -> int:
    """Import providers from CSV. All imported records have is_dummy=False."""
    count = 0
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = float(row["lat"])
            lng = float(row["lng"])
            provider = Provider(
                id=uuid.uuid4(),
                name=row["name"],
                type=row["type"],
                address=row["address"],
                city=row["city"],
                location=f"SRID=4326;POINT({lng} {lat})",
                phone=row.get("phone") or None,
                whatsapp=row.get("whatsapp") or None,
                opening_hours={"24x7": True} if row.get("hours_24x7") == "true" else {},
                timezone=row.get("timezone", "Asia/Kolkata"),
                registration_number=row.get("registration_number") or None,
                verification_status=row.get("verification_status", "pending"),
                walk_in_available=row.get("walk_in_available", "true").lower() == "true",
                is_dummy=False,  # Always false for CSV imports
            )
            session.add(provider)
            count += 1
    session.commit()
    return count


def import_doctors(filepath: Path, session: Session) -> int:
    """Import doctors from CSV. Requires provider_id and specialty_slug."""
    count = 0
    # Build lookups
    specialties = {s.slug: s.id for s in session.query(Specialty).all()}

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            specialty_id = specialties.get(row.get("specialty_slug", ""))
            doctor = Doctor(
                id=uuid.uuid4(),
                provider_id=uuid.UUID(row["provider_id"]),
                full_name=row["full_name"],
                qualifications=row.get("qualifications") or None,
                specialty_id=specialty_id,
                is_dummy=False,
            )
            session.add(doctor)
            count += 1
    session.commit()
    return count


def import_services(filepath: Path, session: Session) -> int:
    """Import services from CSV."""
    count = 0
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            service = Service(
                id=uuid.uuid4(),
                provider_id=uuid.UUID(row["provider_id"]),
                name=row["name"],
                price_min=float(row["price_min"]) if row.get("price_min") else None,
                price_max=float(row["price_max"]) if row.get("price_max") else None,
                currency=row.get("currency", "INR"),
            )
            session.add(service)
            count += 1
    session.commit()
    return count


IMPORTERS = {
    "providers": import_providers,
    "doctors": import_doctors,
    "services": import_services,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="TravelDoc CSV importer")
    parser.add_argument("filepath", help="Path to the CSV file to import")
    args = parser.parse_args()

    filepath = Path(args.filepath)
    if not filepath.exists():
        print(f"❌ File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    # Determine type from filename
    stem = filepath.stem.lower()
    importer = None
    for key in IMPORTERS:
        if key in stem:
            importer = IMPORTERS[key]
            break

    if importer is None:
        print(
            f"❌ Unknown CSV type. Filename must contain one of: {', '.join(IMPORTERS.keys())}",
            file=sys.stderr,
        )
        sys.exit(1)

    engine = get_sync_engine()
    with Session(engine) as session:
        count = importer(filepath, session)
        print(f"✅ Imported {count} records from {filepath.name}")


if __name__ == "__main__":
    main()
