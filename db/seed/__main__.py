"""
TravelDoc seed script.

Usage:
    python -m db.seed          # Seed without resetting
    python -m db.seed --reset  # Wipe existing data and re-seed

Run inside the API container: docker compose exec api python -m db.seed --reset
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "api"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base
from app.models import (  # noqa: F401
    AnalyticsEvent,
    Doctor,
    DoctorLanguage,
    Language,
    Provider,
    Review,
    SearchRequest,
    Service,
    Specialty,
)

SEED_DIR = Path(__file__).parent


def get_sync_engine():
    settings = get_settings()
    url = settings.database_url_sync
    return create_engine(url, echo=False)


def reset_data(session: Session) -> None:
    """Delete all existing data in dependency order."""
    print("🗑  Resetting data...")
    session.execute(text("DELETE FROM analytics_events"))
    session.execute(text("DELETE FROM reviews"))
    session.execute(text("DELETE FROM search_requests"))
    session.execute(text("DELETE FROM doctor_languages"))
    session.execute(text("DELETE FROM services"))
    session.execute(text("DELETE FROM doctors"))
    session.execute(text("DELETE FROM providers"))
    session.execute(text("DELETE FROM languages"))
    session.execute(text("DELETE FROM specialties"))
    session.commit()
    print("✅ Data reset complete.")


def seed_specialties(session: Session) -> dict[str, Specialty]:
    specialties_data = [
        ("general_physician", "General Physician"),
        ("pediatrics", "Pediatrics"),
        ("dental", "Dental"),
        ("orthopedic", "Orthopedic"),
        ("emergency_care", "Emergency Care"),
        ("dermatology", "Dermatology"),
        ("gastroenterology", "Gastroenterology"),
        ("ent", "ENT (Ear, Nose & Throat)"),
    ]
    specialties = {}
    for slug, name in specialties_data:
        s = Specialty(id=uuid.uuid4(), slug=slug, name=name)
        session.add(s)
        specialties[slug] = s
    session.flush()
    print(f"✅ Seeded {len(specialties)} specialties.")
    return specialties


def seed_languages(session: Session) -> dict[str, Language]:
    languages_data = [
        ("en", "English"),
        ("hi", "Hindi"),
        ("ru", "Russian"),
        ("ar", "Arabic"),
        ("fr", "French"),
        ("de", "German"),
        ("kok", "Konkani"),
    ]
    languages = {}
    for code, name in languages_data:
        lang = Language(id=uuid.uuid4(), code=code, name=name)
        session.add(lang)
        languages[code] = lang
    session.flush()
    print(f"✅ Seeded {len(languages)} languages.")
    return languages


# Goa locations: (name, lat, lng, area)
GOA_LOCATIONS = [
    # Panaji area
    ("Panaji", 15.4909, 73.8278),
    ("Panaji", 15.4989, 73.8319),
    ("Panaji", 15.4850, 73.8225),
    ("Fontainhas", 15.4934, 73.8341),
    # Calangute area
    ("Calangute", 15.5440, 73.7552),
    ("Calangute", 15.5398, 73.7612),
    ("Calangute", 15.5321, 73.7489),
    # Baga area
    ("Baga", 15.5567, 73.7523),
    ("Baga", 15.5612, 73.7498),
    # Mapusa area
    ("Mapusa", 15.5959, 73.8138),
    ("Mapusa", 15.5921, 73.8201),
    ("Mapusa", 15.6012, 73.8089),
    # Margao area
    ("Margao", 15.2832, 73.9862),
    ("Margao", 15.2791, 73.9921),
    ("Margao", 15.2873, 73.9801),
    # Vasco area
    ("Vasco da Gama", 15.3982, 73.8132),
    ("Vasco da Gama", 15.4021, 73.8089),
    # Panjim north
    ("Porvorim", 15.5231, 73.8398),
    ("Porvorim", 15.5189, 73.8441),
    # Anjuna / Vagator
    ("Anjuna", 15.5742, 73.7389),
    ("Vagator", 15.5891, 73.7312),
    # Colva
    ("Colva", 15.2789, 73.9312),
    # Old Goa
    ("Old Goa", 15.5058, 73.9120),
    # Ponda
    ("Ponda", 15.4028, 74.0120),
    # Candolim
    ("Candolim", 15.5181, 73.7612),
    # Dona Paula
    ("Dona Paula", 15.4582, 73.8012),
    # Miramar
    ("Miramar", 15.4712, 73.8098),
    # Siolim
    ("Siolim", 15.6089, 73.7498),
    # Morjim
    ("Morjim", 15.6342, 73.7312),
    # Arambol
    ("Arambol", 15.6821, 73.7041),
]


def build_opening_hours(pattern: str) -> dict:
    """
    Patterns:
      '24x7'      -> {"24x7": true}
      '9-18'      -> Mon-Sat 9:00-18:00, Sun closed
      '9-21'      -> Mon-Sat 9:00-21:00, Sun closed
      '8-20-no-sun' -> Mon-Sat 8:00-20:00, Sun closed
      'split'     -> Mon-Sat 9:00-13:00 + 16:00-20:00, Sun 9:00-13:00
    """
    if pattern == "24x7":
        return {"24x7": True}

    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    if pattern == "9-18":
        hours = {}
        for d in days[:-1]:  # Mon-Sat
            hours[d] = [{"open": "09:00", "close": "18:00"}]
        hours["sun"] = []
        return hours

    if pattern == "9-21":
        hours = {}
        for d in days[:-1]:
            hours[d] = [{"open": "09:00", "close": "21:00"}]
        hours["sun"] = []
        return hours

    if pattern == "8-20-no-sun":
        hours = {}
        for d in days[:-1]:
            hours[d] = [{"open": "08:00", "close": "20:00"}]
        hours["sun"] = []
        return hours

    if pattern == "split":
        hours = {}
        for d in days[:-1]:
            hours[d] = [
                {"open": "09:00", "close": "13:00"},
                {"open": "16:00", "close": "20:00"},
            ]
        hours["sun"] = [{"open": "09:00", "close": "13:00"}]
        return hours

    # Default 9-18
    hours = {}
    for d in days[:-1]:
        hours[d] = [{"open": "09:00", "close": "18:00"}]
    hours["sun"] = []
    return hours


PROVIDERS_DATA = [
    # (name, type, area_idx, phone, whatsapp, hours_pattern, verification, walk_in)
    # Hospitals (10) - mostly 24x7, all verified
    ("Sunrise Demo Hospital", "hospital", 0, "+919876543210", "+919876543210", "24x7", "verified", True),
    ("Goa Demo Medical Centre", "hospital", 9, "+919876543211", "+919876543211", "24x7", "verified", True),
    ("Apollo Demo Hospital Panaji", "hospital", 3, "+919876543212", "+919876543212", "24x7", "verified", True),
    ("Healthway Demo Hospital", "hospital", 12, "+919876543213", "+919876543213", "24x7", "verified", True),
    ("SeaCure Demo Hospital", "hospital", 16, "+919876543214", "+919876543214", "24x7", "verified", True),
    ("Ponda Demo Hospital", "hospital", 23, "+919876543215", "+919876543215", "9-21", "verified", True),
    ("North Goa Demo Hospital", "hospital", 10, "+919876543216", "+919876543216", "24x7", "verified", True),
    ("South Goa Demo Hospital", "hospital", 13, "+919876543217", "+919876543217", "24x7", "verified", True),
    ("Mapusa Demo Medical", "hospital", 11, "+919876543218", "+919876543218", "9-21", "verified", True),
    ("Vasco Demo Hospital", "hospital", 17, "+919876543219", "+919876543219", "24x7", "pending", True),
    # Clinics (12) - mix of hours and verification
    ("Sunrise Demo Clinic", "clinic", 1, "+919876543220", "+919876543220", "9-18", "verified", True),
    ("Beachside Demo Clinic", "clinic", 4, "+919876543221", None, "9-18", "verified", True),
    ("Calangute Demo Health Centre", "clinic", 5, "+919876543222", "+919876543222", "9-21", "verified", False),
    ("Baga Beach Demo Clinic", "clinic", 7, "+919876543223", "+919876543223", "9-18", "pending", True),
    ("Anjuna Demo Clinic", "clinic", 19, "+919876543224", "+919876543224", "split", "verified", True),
    ("Mapusa Demo Clinic", "clinic", 10, "+919876543225", "+919876543225", "9-18", "verified", False),
    ("Colva Demo Health Clinic", "clinic", 21, "+919876543226", None, "9-18", "pending", True),
    ("Porvorim Demo Clinic", "clinic", 17, "+919876543227", "+919876543227", "split", "verified", True),
    ("Candolim Demo Clinic", "clinic", 24, "+919876543228", "+919876543228", "9-21", "verified", True),
    ("Miramar Demo Clinic", "clinic", 26, "+919876543229", "+919876543229", "9-18", "pending", False),
    ("Old Goa Demo Clinic", "clinic", 22, "+919876543230", "+919876543230", "split", "verified", True),
    ("Vagator Demo Clinic", "clinic", 20, "+919876543231", None, "9-18", "pending", True),
    # Independent doctors (8)
    ("Dr. Demo Sharma - General Physician", "independent_doctor", 2, "+919876543232", "+919876543232", "9-18", "verified", True),
    ("Dr. Demo Fernandes - Pediatrician", "independent_doctor", 6, "+919876543233", "+919876543233", "9-18", "verified", False),
    ("Dr. Demo Naik - Dentist", "independent_doctor", 25, "+919876543234", "+919876543234", "split", "verified", True),
    ("Dr. Demo Singh - Orthopedic", "independent_doctor", 15, "+919876543235", "+919876543235", "9-18", "pending", True),
    ("Dr. Demo Pereira - Dermatologist", "independent_doctor", 8, "+919876543236", "+919876543236", "9-18", "verified", False),
    ("Dr. Demo Kamat - ENT Specialist", "independent_doctor", 18, "+919876543237", "+919876543237", "split", "pending", True),
    ("Dr. Demo Rodrigues - Gastroenterologist", "independent_doctor", 27, "+919876543238", "+919876543238", "9-18", "verified", False),
    ("Dr. Demo Pillai - General Physician", "independent_doctor", 28, "+919876543239", "+919876543239", "9-18", "pending", True),
]

# Doctors: (full_name, qualifications, specialty_slug, is_dummy)
# Map provider index -> list of doctors
DOCTORS_BY_PROVIDER = {
    # Hospitals: 2-3 doctors each
    0: [("Dr. Demo Amit Sharma", "MBBS, MD (General Medicine)", "general_physician"), ("Dr. Demo Priya Nair", "MBBS, MS (Orthopedics)", "orthopedic"), ("Dr. Demo Fatima Al-Hassan", "MBBS, MD (Emergency Medicine)", "emergency_care")],
    1: [("Dr. Demo Rahul Desai", "MBBS, MD (General Medicine)", "general_physician"), ("Dr. Demo Olga Petrova", "MBBS, MD (Pediatrics)", "pediatrics"), ("Dr. Demo Suresh Kumar", "MBBS, MS (Dental)", "dental")],
    2: [("Dr. Demo Anjali Patel", "MBBS, MD (General Medicine)", "general_physician"), ("Dr. Demo Mohammed Al-Rashid", "MBBS, MD (Gastroenterology)", "gastroenterology")],
    3: [("Dr. Demo Vikram Rao", "MBBS, MD (Emergency Medicine)", "emergency_care"), ("Dr. Demo Sunita Mishra", "MBBS, MD (Dermatology)", "dermatology"), ("Dr. Demo Jean-Pierre Moreau", "MBBS, MD (ENT)", "ent")],
    4: [("Dr. Demo Ravi Pillai", "MBBS, MD (General Medicine)", "general_physician"), ("Dr. Demo Nadia Volkov", "MBBS, MS (Orthopedics)", "orthopedic")],
    5: [("Dr. Demo Santosh Naik", "MBBS, MD (General Medicine)", "general_physician"), ("Dr. Demo Aisha Rahman", "MBBS, MD (Pediatrics)", "pediatrics"), ("Dr. Demo Klaus Muller", "MBBS, MS (Dental)", "dental")],
    6: [("Dr. Demo Patricia Fernandes", "MBBS, MD (Emergency Medicine)", "emergency_care"), ("Dr. Demo Ramesh Gawas", "MBBS, MD (General Medicine)", "general_physician")],
    7: [("Dr. Demo Meera Joshi", "MBBS, MD (Gastroenterology)", "gastroenterology"), ("Dr. Demo Alexei Sokolov", "MBBS, MD (Dermatology)", "dermatology"), ("Dr. Demo Fatima Hassan", "MBBS, MS (Orthopedics)", "orthopedic")],
    8: [("Dr. Demo Deepak Kamat", "MBBS, MD (General Medicine)", "general_physician"), ("Dr. Demo Ivan Petrov", "MBBS, MD (Emergency Medicine)", "emergency_care")],
    9: [("Dr. Demo Laxmi Naik", "MBBS, MD (General Medicine)", "general_physician"), ("Dr. Demo Ahmed Al-Farsi", "MBBS, MS (Orthopedics)", "orthopedic")],
    # Clinics: 1-2 doctors each
    10: [("Dr. Demo Sanjay Verma", "MBBS, MD (General Medicine)", "general_physician"), ("Dr. Demo Elena Kozlov", "MBBS, MD (Pediatrics)", "pediatrics")],
    11: [("Dr. Demo Carlos Fernandes", "MBBS, MD (General Medicine)", "general_physician")],
    12: [("Dr. Demo Pooja Shirsat", "MBBS, MD (General Medicine)", "general_physician"), ("Dr. Demo Yusuf Al-Amin", "MBBS, MS (Dental)", "dental")],
    13: [("Dr. Demo Maria Pereira", "MBBS, MD (General Medicine)", "general_physician")],
    14: [("Dr. Demo Dmitri Volkov", "MBBS, MD (Dermatology)", "dermatology"), ("Dr. Demo Sunita Rao", "MBBS, MD (General Medicine)", "general_physician")],
    15: [("Dr. Demo Rajesh Naik", "MBBS, MD (General Medicine)", "general_physician"), ("Dr. Demo Fatou Diallo", "MBBS, MD (Pediatrics)", "pediatrics")],
    16: [("Dr. Demo Anjana Couto", "MBBS, MD (General Medicine)", "general_physician")],
    17: [("Dr. Demo Pradeep Sawant", "MBBS, MD (General Medicine)", "general_physician"), ("Dr. Demo Natasha Ivanova", "MBBS, MD (ENT)", "ent")],
    18: [("Dr. Demo George Monteiro", "MBBS, MD (General Medicine)", "general_physician"), ("Dr. Demo Hamid Al-Sayed", "MBBS, MS (Dental)", "dental")],
    19: [("Dr. Demo Sneha Desai", "MBBS, MD (General Medicine)", "general_physician")],
    20: [("Dr. Demo Francis D'Souza", "MBBS, MD (General Medicine)", "general_physician"), ("Dr. Demo Olga Sidorova", "MBBS, MD (Gastroenterology)", "gastroenterology")],
    21: [("Dr. Demo Rahul Palekar", "MBBS, MD (General Medicine)", "general_physician")],
    # Independent doctors: 1 doctor each
    22: [("Dr. Demo Sharma", "MBBS, MD (General Medicine)", "general_physician")],
    23: [("Dr. Demo Fernandes", "MBBS, MD (Pediatrics)", "pediatrics")],
    24: [("Dr. Demo Naik", "BDS, MDS (Dental)", "dental")],
    25: [("Dr. Demo Singh", "MBBS, MS (Orthopedics)", "orthopedic")],
    26: [("Dr. Demo Pereira", "MBBS, MD (Dermatology)", "dermatology")],
    27: [("Dr. Demo Kamat", "MBBS, MS (ENT)", "ent")],
    28: [("Dr. Demo Rodrigues", "MBBS, MD (Gastroenterology)", "gastroenterology")],
    29: [("Dr. Demo Pillai", "MBBS, MD (General Medicine)", "general_physician")],
}

# Language assignments per provider index
# Format: {provider_idx: [(lang_code, proficiency), ...]}
LANGUAGE_ASSIGNMENTS = {
    # Hospitals: broad language coverage
    0: [("en", "fluent"), ("hi", "native"), ("kok", "native"), ("ru", "fluent")],
    1: [("en", "fluent"), ("hi", "native"), ("ru", "native"), ("kok", "basic")],
    2: [("en", "native"), ("hi", "fluent"), ("ar", "fluent"), ("kok", "basic")],
    3: [("en", "fluent"), ("hi", "native"), ("fr", "fluent"), ("kok", "native")],
    4: [("en", "fluent"), ("hi", "native"), ("ru", "fluent"), ("kok", "basic")],
    5: [("en", "fluent"), ("hi", "native"), ("de", "fluent"), ("kok", "native")],
    6: [("en", "fluent"), ("kok", "native"), ("hi", "fluent")],
    7: [("en", "fluent"), ("hi", "native"), ("ru", "native"), ("ar", "basic")],
    8: [("en", "native"), ("hi", "native"), ("ru", "fluent")],
    9: [("en", "fluent"), ("hi", "native"), ("ar", "fluent"), ("kok", "basic")],
    # Clinics
    10: [("en", "fluent"), ("hi", "native"), ("ru", "fluent")],
    11: [("en", "fluent"), ("kok", "native"), ("hi", "basic")],
    12: [("en", "fluent"), ("hi", "native"), ("ar", "fluent")],
    13: [("en", "basic"), ("kok", "native"), ("hi", "fluent")],
    14: [("en", "fluent"), ("ru", "native"), ("de", "basic")],
    15: [("en", "fluent"), ("hi", "native"), ("kok", "native")],
    16: [("kok", "native"), ("en", "basic"), ("hi", "fluent")],
    17: [("en", "fluent"), ("hi", "native"), ("ru", "fluent")],
    18: [("en", "fluent"), ("ar", "native"), ("hi", "fluent")],
    19: [("en", "basic"), ("kok", "native"), ("hi", "native")],
    20: [("en", "fluent"), ("kok", "native"), ("ru", "basic")],
    21: [("en", "fluent"), ("ru", "native"), ("hi", "basic")],
    # Independent doctors
    22: [("en", "fluent"), ("hi", "native"), ("kok", "fluent")],
    23: [("en", "fluent"), ("kok", "native"), ("hi", "fluent")],
    24: [("en", "fluent"), ("kok", "native"), ("hi", "native")],
    25: [("en", "fluent"), ("hi", "native"), ("kok", "basic")],
    26: [("en", "fluent"), ("ru", "fluent"), ("hi", "basic")],
    27: [("en", "basic"), ("kok", "native"), ("hi", "native")],
    28: [("en", "fluent"), ("kok", "native"), ("hi", "fluent")],
    29: [("en", "basic"), ("hi", "native"), ("kok", "native")],
}

# Services: (name, price_min, price_max) — provider type determines which
HOSPITAL_SERVICES = [
    ("general_consultation", 500, 1500),
    ("emergency_care", 1000, 5000),
    ("xray", 500, 1500),
    ("basic_blood_test", 400, 1200),
    ("stitches", 800, 3000),
]

CLINIC_SERVICES = [
    ("general_consultation", 300, 800),
    ("fever_treatment", 300, 800),
    ("basic_blood_test", 300, 800),
    ("minor_injury_dressing", 200, 600),
    ("stomach_issue_treatment", 300, 700),
]

SPECIALTY_SERVICES = {
    "dental": [("dental_checkup", 400, 1000), ("general_consultation", 400, 1000)],
    "orthopedic": [("general_consultation", 600, 1500), ("xray", 500, 1200)],
    "dermatology": [("general_consultation", 500, 1200)],
    "pediatrics": [("general_consultation", 400, 900), ("fever_treatment", 300, 700)],
    "gastroenterology": [("general_consultation", 600, 1500), ("stomach_issue_treatment", 500, 1000)],
    "ent": [("general_consultation", 500, 1200)],
    "emergency_care": [("emergency_care", 1000, 5000), ("stitches", 800, 3000)],
    "general_physician": [("general_consultation", 300, 800), ("fever_treatment", 300, 700)],
}

DUMMY_REVIEWS_DATA = [
    # (provider_idx, rating, amount, comment)
    (0, 5, 500, "Excellent service! Staff was very helpful."),
    (0, 4, 450, "Quick and professional."),
    (1, 4, 600, "Good doctors, clean facility."),
    (2, 5, 1200, "Dr. Patel was fantastic. Highly recommended."),
    (3, 4, 800, "Great emergency care team."),
    (4, 3, 700, "Decent service but waiting time was long."),
    (5, 5, 500, "Wonderful experience. Very thorough."),
    (6, 4, 400, "Professional and efficient."),
    (7, 5, 900, "Best hospital in the area!"),
    (8, 4, 650, "Good service overall."),
    (10, 4, 450, "Quick consultation, helpful doctor."),
    (11, 5, 350, "Very friendly and knowledgeable."),
    (12, 4, 500, "Good clinic, reasonable prices."),
    (14, 5, 600, "Excellent dermatologist!"),
    (17, 4, 400, "Convenient location and good service."),
    (18, 5, 700, "Arabic-speaking staff made me feel comfortable."),
    (22, 5, 400, "Dr. Sharma is the best! Very thorough."),
    (23, 4, 500, "Great pediatrician for my kids."),
    (24, 5, 600, "Excellent dental work. Pain-free experience!"),
    (25, 4, 800, "Good orthopedic consultation."),
]


def seed_data(session: Session, reset: bool = False) -> None:
    if reset:
        reset_data(session)

    print("🌱 Seeding database...")

    specialties = seed_specialties(session)
    languages = seed_languages(session)

    now_dt = datetime.now(timezone.utc)
    verified_at = datetime(2024, 1, 15, tzinfo=timezone.utc)

    provider_objects = []

    for idx, (name, ptype, loc_idx, phone, whatsapp, hours_pattern, verification, walk_in) in enumerate(PROVIDERS_DATA):
        area, lat, lng = GOA_LOCATIONS[loc_idx]
        address = f"Demo Street {idx + 1}, {area}, Goa - {400001 + idx}"

        # Create WKT point for PostGIS
        location_wkt = f"POINT({lng} {lat})"

        provider = Provider(
            id=uuid.uuid4(),
            name=name,
            type=ptype,
            address=address,
            city="Goa",
            location=f"SRID=4326;{location_wkt}",
            phone=phone,
            whatsapp=whatsapp,
            opening_hours=build_opening_hours(hours_pattern),
            timezone="Asia/Kolkata",
            registration_number=f"GOA-MED-{2020 + idx:04d}",
            verification_status=verification,
            last_verified_at=verified_at if verification == "verified" else None,
            walk_in_available=walk_in,
            is_dummy=True,
        )
        session.add(provider)
        provider_objects.append(provider)

    session.flush()

    # Seed doctors and their languages
    all_doctors: list[tuple[int, Doctor]] = []
    for prov_idx, doctor_list in DOCTORS_BY_PROVIDER.items():
        provider = provider_objects[prov_idx]
        for doc_name, qualifications, specialty_slug in doctor_list:
            doctor = Doctor(
                id=uuid.uuid4(),
                provider_id=provider.id,
                full_name=doc_name,
                qualifications=qualifications,
                specialty_id=specialties[specialty_slug].id,
                is_dummy=True,
            )
            session.add(doctor)
            all_doctors.append((prov_idx, doctor))

    session.flush()

    # Assign languages to doctors
    for prov_idx, doctor in all_doctors:
        lang_assignments = LANGUAGE_ASSIGNMENTS.get(prov_idx, [("en", "fluent")])
        for lang_code, proficiency in lang_assignments:
            if lang_code in languages:
                dl = DoctorLanguage(
                    doctor_id=doctor.id,
                    language_id=languages[lang_code].id,
                    proficiency=proficiency,
                )
                session.add(dl)

    session.flush()

    # Seed services
    for idx, (name, ptype, *_) in enumerate(PROVIDERS_DATA):
        provider = provider_objects[idx]
        if ptype == "hospital":
            service_list = HOSPITAL_SERVICES
        elif ptype == "clinic":
            service_list = CLINIC_SERVICES
        else:
            # Independent doctor: use specialty services
            doctors_for_provider = DOCTORS_BY_PROVIDER.get(idx, [])
            primary_specialty = doctors_for_provider[0][2] if doctors_for_provider else "general_physician"
            service_list = SPECIALTY_SERVICES.get(primary_specialty, CLINIC_SERVICES)

        for svc_name, price_min, price_max in service_list:
            service = Service(
                id=uuid.uuid4(),
                provider_id=provider.id,
                name=svc_name,
                price_min=price_min,
                price_max=price_max,
                currency="INR",
                last_verified_at=verified_at,
            )
            session.add(service)

    session.flush()

    # Seed dummy approved reviews
    for prov_idx, rating, amount, comment in DUMMY_REVIEWS_DATA:
        provider = provider_objects[prov_idx]
        review = Review(
            id=uuid.uuid4(),
            provider_id=provider.id,
            search_request_id=None,
            rating=rating,
            actual_amount_paid=amount,
            currency="INR",
            comment=comment,
            status="approved",
        )
        session.add(review)

    session.commit()
    print(f"✅ Seeded {len(PROVIDERS_DATA)} providers, {len(all_doctors)} doctors, {len(DUMMY_REVIEWS_DATA)} reviews.")
    print("🎉 Seed complete!")


def main() -> None:
    parser = argparse.ArgumentParser(description="TravelDoc seed script")
    parser.add_argument("--reset", action="store_true", help="Wipe existing data before seeding")
    args = parser.parse_args()

    engine = get_sync_engine()
    with Session(engine) as session:
        seed_data(session, reset=args.reset)


if __name__ == "__main__":
    main()
