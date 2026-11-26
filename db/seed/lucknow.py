"""
Lucknow real-world doctors & providers seed script for TravelDoc.

Usage:
    python -m db.seed.lucknow          # Add Lucknow data
    python -m db.seed.lucknow --reset  # Wipe existing data and seed Lucknow data

Run inside the API container:
    docker compose exec api python -m db.seed.lucknow --reset
"""
from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "api"))

from sqlalchemy.orm import Session

from app.models import (  # noqa: F401
    Doctor,
    DoctorLanguage,
    Provider,
    Service,
)
from db.seed.__main__ import (
    CLINIC_SERVICES,
    HOSPITAL_SERVICES,
    SPECIALTY_SERVICES,
    build_opening_hours,
    get_sync_engine,
    reset_data,
    seed_languages,
    seed_specialties,
)

# Real Lucknow Healthcare Providers:
# (name, type, address, lat, lng, phone, hours_pattern, walk_in)
LUCKNOW_PROVIDERS = [
    # --- Major Hospitals (14) ---
    (
        "Medanta Hospital, Lucknow",
        "hospital",
        "Sector A, Pocket 1, Sushant Golf City, Amar Shaheed Path, Lucknow - 226030",
        26.77728,
        80.98565,
        "+915224514000",
        "24x7",
        True,
    ),
    (
        "ApolloMedics Super Speciality Hospital",
        "hospital",
        "KBC-31, Kanpur-Lucknow Rd, Sector B, Bargawan, LDA Colony, Lucknow - 226012",
        26.79850,
        80.90450,
        "+915226788888",
        "24x7",
        True,
    ),
    (
        "Max Super Speciality Hospital (Sahara Hospital)",
        "hospital",
        "Viraj Khand, Gomti Nagar, Lucknow - 226010",
        26.85050,
        81.02430,
        "+915226780001",
        "24x7",
        True,
    ),
    (
        "Chandan Hospital",
        "hospital",
        "Faizabad Rd, Vijayant Khand, Gomti Nagar, Lucknow - 226010",
        26.87390,
        81.02310,
        "+915226666600",
        "24x7",
        True,
    ),
    (
        "Vivekananda Polyclinic & Institute of Medical Sciences",
        "hospital",
        "Vivekananda Puram, Nirala Nagar, Lucknow - 226007",
        26.87410,
        80.94000,
        "+915222321277",
        "24x7",
        True,
    ),
    (
        "Mayo Medical Centre (Dr. KNS Memorial Hospital)",
        "hospital",
        "Vikas Khand 2, Gomti Nagar, Lucknow - 226010",
        26.84950,
        81.00650,
        "+915222398611",
        "24x7",
        True,
    ),
    (
        "King George's Medical University (KGMU)",
        "hospital",
        "Shah Mina Rd, Chowk, Lucknow - 226003",
        26.86700,
        80.91590,
        "+915222258880",
        "24x7",
        True,
    ),
    (
        "Sanjay Gandhi Postgraduate Institute (SGPGIMS)",
        "hospital",
        "Raebareli Rd, Haibat Mau Mawaiya, Lucknow - 226014",
        26.74640,
        80.93610,
        "+915222668700",
        "24x7",
        True,
    ),
    (
        "Avadh Hospital & Heart Centre",
        "hospital",
        "Avadh Hospital Chauraha, Singar Nagar, Alambagh, Lucknow - 226005",
        26.80150,
        80.89500,
        "+915222462462",
        "24x7",
        True,
    ),
    (
        "Shekhar Hospital",
        "hospital",
        "B-Block, Church Rd, Indira Nagar, Lucknow - 226016",
        26.88330,
        80.98330,
        "+915222352352",
        "24x7",
        True,
    ),
    (
        "Charak Hospital & Research Centre",
        "hospital",
        "Hardoi Rd, Dubagga, Lucknow - 226003",
        26.87800,
        80.86900,
        "+915222405601",
        "24x7",
        True,
    ),
    (
        "Midland Healthcare & Research Center",
        "hospital",
        "B-55, Mandir Marg, Mahanagar Extension, Lucknow - 226006",
        26.87750,
        80.95620,
        "+915222335500",
        "24x7",
        True,
    ),
    (
        "Ford Hospital",
        "hospital",
        "Near Patrakarpuram Crossing, Vikas Khand, Gomti Nagar, Lucknow - 226010",
        26.85400,
        81.00100,
        "+915224004400",
        "24x7",
        True,
    ),
    (
        "Regency Hospital Lucknow",
        "hospital",
        "Khurram Nagar, Ring Rd, Lucknow - 226022",
        26.89200,
        80.97100,
        "+915223500111",
        "24x7",
        True,
    ),
    (
        "Lok Bandhu Raj Narayan Combined Hospital",
        "hospital",
        "LDA Colony, Kanpur Rd, Ashiyana, Lucknow - 226012",
        26.79500,
        80.90900,
        "+915222421112",
        "24x7",
        True,
    ),
    (
        "Nova Hospital",
        "hospital",
        "Vikas Khand 1, Patrakarpuram Rd, Gomti Nagar, Lucknow - 226010",
        26.85320,
        81.00380,
        "+915224001122",
        "24x7",
        True,
    ),
    (
        "Ajanta Hospital & IVF Centre",
        "hospital",
        "765, ABC Complex, Kanpur Rd, Alambagh, Lucknow - 226005",
        26.80750,
        80.89950,
        "+915222462525",
        "24x7",
        True,
    ),
    # --- Clinics & Independent Doctors (15) ---
    (
        "Fracture Arthritis & Joint Replacement Clinic",
        "clinic",
        "Park Rd, Opposite New Civil Hospital, Hazratganj, Lucknow - 226001",
        26.85300,
        80.94650,
        "+915222238100",
        "split",
        True,
    ),
    (
        "Casting Smiles Dental Care Center",
        "clinic",
        "LGF 19-C, Vidhan Sabha Marg, Near All India Radio, Hazratganj, Lucknow - 226001",
        26.84900,
        80.94100,
        "+915224012345",
        "9-21",
        True,
    ),
    (
        "Dental Care Clinic (Hazratganj)",
        "clinic",
        "#3, Newal Kishore Rd, Near Ashok Marg, Hazratganj, Lucknow - 226001",
        26.85500,
        80.94450,
        "+915222624567",
        "9-18",
        True,
    ),
    (
        "Civil Dental Clinic",
        "clinic",
        "2nd Floor, AF Tower, 5 Park Rd, Opposite Civil Hospital, Hazratganj, Lucknow - 226001",
        26.85320,
        80.94680,
        "+915222234890",
        "9-21",
        True,
    ),
    (
        "Derma Klinic",
        "clinic",
        "Creation Square, 29/29 Ka 3A, Rana Pratap Marg, Hazratganj, Lucknow - 226001",
        26.85800,
        80.94750,
        "+915224045566",
        "9-21",
        True,
    ),
    (
        "Dr. A. K. Jain's Clinic",
        "independent_doctor",
        "MG Marg, Hazratganj, Lucknow - 226001",
        26.85550,
        80.94300,
        "+915222618899",
        "split",
        True,
    ),
    (
        "Sarthak Child Clinic",
        "clinic",
        "Sector 14, Indira Nagar, Lucknow - 226016",
        26.88500,
        80.98500,
        "+915222714433",
        "split",
        True,
    ),
    (
        "Shourya Polyclinic & Vaccination Centre",
        "clinic",
        "Bhootnath Market Area, Indira Nagar, Lucknow - 226016",
        26.88100,
        80.98000,
        "+915222341122",
        "9-21",
        True,
    ),
    (
        "The Velvet Skin Centre",
        "clinic",
        "23, Amrapali Market, Block B, Indira Nagar, Lucknow - 226016",
        26.88400,
        80.98700,
        "+915224071199",
        "9-21",
        True,
    ),
    (
        "Indira Clinic & Orthopaedic Centre",
        "clinic",
        "Sector J, Aliganj, Lucknow - 226024",
        26.90520,
        80.94800,
        "+915222367788",
        "split",
        True,
    ),
    (
        "Dr. B. M. Agarwal Clinic",
        "independent_doctor",
        "Near Qaiserbagh Bus Stand, Nala Fatehganj, Aminabad, Lucknow - 226018",
        26.84630,
        80.92630,
        "+915222629900",
        "9-18",
        True,
    ),
    (
        "Tooth n Implants Dental Clinic",
        "clinic",
        "Chowk Main Market, Chowk, Lucknow - 226003",
        26.86330,
        80.90330,
        "+915222253344",
        "9-21",
        True,
    ),
    (
        "Fatima Health Clinic",
        "clinic",
        "Katra Abutrab Khana, Chowk, Lucknow - 226003",
        26.86200,
        80.90500,
        "+915222256677",
        "split",
        True,
    ),
    (
        "The Rainbow Clinic",
        "clinic",
        "Vijay Khand, Gomti Nagar, Lucknow - 226010",
        26.84650,
        81.00800,
        "+915224029988",
        "split",
        True,
    ),
    (
        "Rohatgi's Child Care Clinic",
        "clinic",
        "Gol Market, Mahanagar, Lucknow - 226006",
        26.87850,
        80.95700,
        "+915222334455",
        "split",
        True,
    ),
]

# 108 Real Doctors mapped to their real Lucknow Providers:
# provider_idx -> [(full_name, qualifications, specialty_slug), ...]
LUCKNOW_DOCTORS_BY_PROVIDER = {
    # 0: Medanta Hospital (14 doctors)
    0: [
        ("Dr. Harsh Kaushal", "MBBS, MD (Internal Medicine)", "general_physician"),
        ("Dr. Sakshi Manchanda", "MBBS, MD (Internal Medicine)", "general_physician"),
        ("Dr. Ruchita Sharma", "MBBS, MD (Internal Medicine)", "general_physician"),
        ("Dr. Ila Pandey", "MBBS, MD (Internal Medicine)", "general_physician"),
        ("Dr. Arvinder Gandhi", "MBBS, MD (Internal Medicine)", "general_physician"),
        ("Dr. Aakash Pandita", "MBBS, MD (Pediatrics), DM (Neonatology)", "pediatrics"),
        ("Dr. Shyamendra Pratap Sharma", "MBBS, MS, MCh (Pediatric Surgery)", "pediatrics"),
        ("Dr. Jaya Pandey", "MBBS, MD (Pediatrics)", "pediatrics"),
        ("Dr. Shefali Porwal", "MBBS, MD (Dermatology)", "dermatology"),
        ("Dr. Abhai Verma", "MBBS, MD, DM (Gastroenterology)", "gastroenterology"),
        ("Dr. Anand Prakash", "MBBS, MS, MCh (Surgical Gastroenterology)", "gastroenterology"),
        ("Dr. Bharat Sangal", "MBBS, MS, MCh (GI Surgery)", "gastroenterology"),
        ("Dr. Manoj Kumar Mishra", "MBBS, MS (ENT, Head & Neck Surgery)", "ent"),
        ("Dr. Kanika Arora", "MBBS, MS (ENT & Neuro-Otology)", "ent"),
    ],
    # 1: ApolloMedics Super Speciality Hospital (17 doctors)
    1: [
        ("Dr. Mayank Somani", "MBBS, MD (Internal Medicine)", "general_physician"),
        ("Dr. Arpit Taunk", "MBBS, MD (Medicine)", "general_physician"),
        ("Dr. Kamal Kishor Gupta", "MBBS, MS (Orthopedics)", "orthopedic"),
        ("Dr. Narinder Kumar", "MBBS, MS (Orthopedics)", "orthopedic"),
        ("Dr. Prakash Gaurav Tewari", "MBBS, MS (Orthopedics & Spine)", "orthopedic"),
        ("Dr. Apoorv Kumar", "MBBS, MS (Spine Surgery)", "orthopedic"),
        ("Dr. Siddharth Shelat", "BDS, MDS (Dental Surgery)", "dental"),
        ("Dr. Utkarsh Singh", "BDS, MDS (Dental Surgery)", "dental"),
        ("Dr. Archit Dhawan", "BDS, MDS (Dental Surgery)", "dental"),
        ("Dr. Ravi Sagar Singh Shahi", "BDS, MDS (Dental Surgery)", "dental"),
        ("Dr. Rajiv Khanna", "MBBS, MS (ENT)", "ent"),
        ("Dr. Salman Khan", "MBBS, MS (ENT)", "ent"),
        ("Dr. Akriti Agrawal", "MBBS, MD (Dermatology)", "dermatology"),
        ("Dr. Pragati Gogia Jain", "MBBS, MD (Dermatology)", "dermatology"),
        ("Dr. Jayendra Shukla", "MBBS, MD, DM (Gastroenterology)", "gastroenterology"),
        ("Dr. Rajiv Ranjan Singh", "MBBS, MD, DM (Hepatology)", "gastroenterology"),
        ("Dr. Waliullah Siddiqui", "MBBS, MS, DNB (Gastroenterology)", "gastroenterology"),
    ],
    # 2: Max / Sahara Hospital (3 doctors)
    2: [
        ("Dr. Ankur Gupta", "MBBS, MD, DM (Gastroenterology)", "gastroenterology"),
        ("Dr. Daya Ram", "MBBS, MD, DNB (Gastroenterology)", "gastroenterology"),
        ("Dr. Puneet Gupta", "MBBS, MS, MCh (GI Surgery)", "gastroenterology"),
    ],
    # 3: Chandan Hospital (10 doctors)
    3: [
        ("Dr. Anurag Srivastava", "MBBS, MD (General Medicine)", "general_physician"),
        ("Dr. A. K. Singh", "MBBS, MD (General & Pulmonary Medicine)", "general_physician"),
        ("Dr. Narendra", "MBBS, MD (Pediatrics)", "pediatrics"),
        ("Dr. Sunil Kanoujia", "MBBS, MS, MCh (Pediatric Surgery)", "pediatrics"),
        ("Dr. Sandeep Kumar Kesharwani", "MBBS, MS (Orthopedics)", "orthopedic"),
        ("Dr. Raju Kumar", "MBBS, MD, DM (Gastroenterology)", "gastroenterology"),
        ("Dr. Shivam Sachan", "MBBS, MD, DM (Gastroenterology)", "gastroenterology"),
        ("Dr. Alankar Kumar Gupta", "MBBS, MS, DNB (Surgical Gastroenterology)", "gastroenterology"),
        ("Dr. Priyanjal", "MBBS, MS (ENT)", "ent"),
        ("Dr. Rajat Jain", "MBBS, MS (ENT)", "ent"),
    ],
    # 4: Vivekananda Polyclinic (9 doctors)
    4: [
        ("Dr. Naresh Rajpal", "MBBS, MD (General Medicine)", "general_physician"),
        ("Dr. Arun Sachdeva", "MBBS, MD (General Medicine)", "general_physician"),
        ("Dr. Jawed Ahmad", "MBBS, MD (General Medicine)", "general_physician"),
        ("Dr. Sudhir Kumar", "MBBS, MD (General Medicine)", "general_physician"),
        ("Dr. Navneet Tripathi", "MBBS, MD (Medicine & Diabetology)", "general_physician"),
        ("Dr. Kanchan Porwal", "MBBS, MD (Dermatology)", "dermatology"),
        ("Dr. Rohit Gupta", "MBBS, MD (Dermatology)", "dermatology"),
        ("Dr. Pragya Mishra", "MBBS, MD (Dermatology)", "dermatology"),
        ("Dr. Ujjawal Maheshwari", "MBBS, MD (Internal Medicine)", "general_physician"),
    ],
    # 5: Mayo Medical Centre (8 doctors)
    5: [
        ("Dr. S. M. A. Rizwi", "MBBS, MD (General Medicine)", "general_physician"),
        ("Dr. Sanjay Kumar Srivastava", "MBBS, MS (Orthopedics)", "orthopedic"),
        ("Dr. Abdur Rehman", "MBBS, MS (ENT)", "ent"),
        ("Dr. Zeeshan", "MBBS, MS (ENT)", "ent"),
        ("Dr. Varsha Dubey", "MBBS, MD (Dermatology)", "dermatology"),
        ("Dr. Vinay Raj Pandey", "BDS, MDS (Maxillofacial & Dental Surgery)", "dental"),
        ("Dr. Rachit Raj", "MBBS, MS (Emergency & General Surgery)", "emergency_care"),
        ("Dr. Rahul Singh", "MBBS, MS (Emergency & Trauma Care)", "emergency_care"),
    ],
    # 6: KGMU (14 doctors)
    6: [
        ("Dr. S. N. Singh", "MBBS, MD (Pediatrics & Neonatology)", "pediatrics"),
        ("Dr. Chandrakanta", "MBBS, MD (Pediatric Neurology)", "pediatrics"),
        ("Dr. Rajesh Kumar Yadav", "MBBS, MD (Pediatric Critical Care)", "emergency_care"),
        ("Dr. R. N. Srivastava", "MBBS, MS (Orthopedics)", "orthopedic"),
        ("Dr. Ajai Singh", "MBBS, MS (Pediatric Orthopedics)", "orthopedic"),
        ("Dr. Najmul Huda", "MBBS, MS (Orthopedics)", "orthopedic"),
        ("Dr. Vikas Verma", "MBBS, MS (Orthopedics)", "orthopedic"),
        ("Prof. A. Mishra", "MBBS, MS (ENT, Head & Neck Surgery)", "ent"),
        ("Prof. Veerendra Verma", "MBBS, MS (ENT)", "ent"),
        ("Dr. Hitendra Prakash Singh", "MBBS, MS (ENT)", "ent"),
        ("Dr. Sunil Kumar", "MBBS, MS (ENT)", "ent"),
        ("Dr. Manish Chandra", "MBBS, MS (ENT)", "ent"),
        ("Dr. Abhishek Bahadur Singh", "MBBS, MS (ENT)", "ent"),
        ("Dr. Sumit Rungta", "MBBS, MD, DM (Gastroenterology)", "gastroenterology"),
    ],
    # 7: SGPGIMS (14 doctors)
    7: [
        ("Prof. Praveer Rai", "MBBS, MD, DM (Gastroenterology)", "gastroenterology"),
        ("Prof. Samir Mohindra", "MBBS, MD, DM (Gastroenterology)", "gastroenterology"),
        ("Prof. Gaurav Pandey", "MBBS, MD, DM (Gastroenterology)", "gastroenterology"),
        ("Dr. Anshuman Elhence", "MBBS, MD, DM (Gastroenterology)", "gastroenterology"),
        ("Dr. Anugrah Dhooria", "MBBS, MD, DM (Gastroenterology)", "gastroenterology"),
        ("Prof. Anshu Srivastava", "MBBS, MD, DM (Pediatric Gastroenterology)", "pediatrics"),
        ("Prof. Laxmi Kant Bharti", "MBBS, MD (Pediatrics)", "pediatrics"),
        ("Dr. Moinak Sen Sarma", "MBBS, MD, DM (Pediatrics)", "pediatrics"),
        ("Dr. Brijesh Singh", "MBBS, MD (General Medicine)", "general_physician"),
        ("Dr. Ajeet Kumar", "MBBS, MD (Dermatology)", "dermatology"),
        ("Prof. Amit Keshri", "MBBS, MS (ENT & Neuro-Otology)", "ent"),
        ("Dr. Indu Shukla", "MBBS, MS (ENT)", "ent"),
        ("Dr. Nazrin Hameed", "MBBS, MS (ENT)", "ent"),
        ("Dr. Rudra Prakash", "MBBS, MS (ENT)", "ent"),
    ],
    # 8: Avadh Hospital (5 doctors)
    8: [
        ("Dr. Vineet Agrawal", "MBBS, MD (General Medicine)", "general_physician"),
        ("Dr. Praveen Kumar Pandey", "MBBS, MD (General Medicine)", "general_physician"),
        ("Dr. Abhinav Gupta", "MBBS, MS (Emergency & General Surgery)", "emergency_care"),
        ("Dr. Abhishek Srivastava", "MBBS, MD (Internal Medicine)", "general_physician"),
        ("Dr. Anurodh Pratap Singh", "MBBS, MD (General Medicine)", "general_physician"),
    ],
    # 9: Shekhar Hospital (5 doctors)
    9: [
        ("Dr. S. K. Gupta", "MBBS, MS (Orthopedics)", "orthopedic"),
        ("Dr. Pratipal Singh", "MBBS, MS (Orthopedics)", "orthopedic"),
        ("Dr. Nishant Kanodia", "MBBS, MD (General Medicine)", "general_physician"),
        ("Dr. G. K. Tripathi", "MBBS, MD (General Medicine)", "general_physician"),
        ("Dr. Vijay Singh", "MBBS, MD (Pediatrics)", "pediatrics"),
    ],
    # 10: Charak Hospital (4 doctors)
    10: [
        ("Dr. Vipul Kumar Gupta", "MBBS, MS (Orthopedics)", "orthopedic"),
        ("Dr. Ashok Kumar", "MBBS, MD (General Medicine)", "general_physician"),
        ("Dr. S. P. Singh", "MBBS, MD (Internal Medicine)", "general_physician"),
        ("Dr. Manish Kumar Jha", "MBBS, MD (General Medicine)", "general_physician"),
    ],
    # 11: Midland Healthcare (3 doctors)
    11: [
        ("Dr. B. P. Singh", "MBBS, MD (General & Pulmonary Medicine)", "general_physician"),
        ("Dr. Tarun Malik", "BDS, MDS (Dental & Maxillofacial)", "dental"),
        ("Dr. Sandeep Agarwal", "MBBS, MD (Internal Medicine)", "general_physician"),
    ],
    # 12: Ford Hospital (3 doctors)
    12: [
        ("Dr. Rakesh Srivastava", "MBBS, MS (ENT)", "ent"),
        ("Dr. Ajay Kr. Choudhary", "MBBS, MD, DM (Gastroenterology)", "gastroenterology"),
        ("Dr. Arun Kumar", "MBBS, MD (General Medicine)", "general_physician"),
    ],
    # 13: Regency Hospital (3 doctors)
    13: [
        ("Dr. Praveen Jha", "MBBS, MD, DM (Gastroenterology)", "gastroenterology"),
        ("Dr. Aditya K. Agrawal", "MBBS, MS (Orthopedics)", "orthopedic"),
        ("Dr. Kiran Suthar", "MBBS, MD (Pediatrics)", "pediatrics"),
    ],
    # 14: Lok Bandhu Hospital (4 doctors)
    14: [
        ("Dr. Vimal Kumar", "MBBS, MD (Dermatology)", "dermatology"),
        ("Dr. Pankaj Gupta", "MBBS, MD (General Medicine)", "general_physician"),
        ("Dr. Rakesh Kumar", "MBBS, MS (ENT)", "ent"),
        ("Dr. Ashok Yadav", "MBBS, MD (Pediatrics)", "pediatrics"),
    ],
    # 15: Nova Hospital (4 doctors)
    15: [
        ("Dr. Aftab Hussain", "MBBS, MD (Internal Medicine)", "general_physician"),
        ("Dr. Shashank Dixit", "MBBS, MD (Internal Medicine)", "general_physician"),
        ("Dr. Arti Rathore", "MBBS, MD (Pediatrics)", "pediatrics"),
        ("Dr. Rani B. Shahi", "MBBS, MS (ENT)", "ent"),
    ],
    # 16: Ajanta Hospital (3 doctors)
    16: [
        ("Dr. M. S. Chhabra", "MBBS, MS (Orthopedics)", "orthopedic"),
        ("Dr. Rishi Dwivedi", "MBBS, MS, FNB (Spine & Orthopedics)", "orthopedic"),
        ("Dr. Anil Khanna", "MBBS, MS (General & Emergency Surgery)", "emergency_care"),
    ],
    # 17-31: Independent Clinics & Doctors (16 doctors)
    17: [("Dr. Sandeep Kapoor", "MBBS, MS (Orthopedics)", "orthopedic")],
    18: [("Dr. Sachin Seth", "BDS, MDS (Dental & Implantology)", "dental")],
    19: [("Dr. Anju Loomba", "BDS, MDS (Dental Surgery)", "dental")],
    20: [("Dr. Anil Kumar", "BDS, MDS (Dental Surgery)", "dental")],
    21: [("Dr. Sonal Tibrewal", "MBBS, MD (Dermatology)", "dermatology")],
    22: [("Dr. A. K. Jain", "MBBS, MD (General Medicine)", "general_physician")],
    23: [("Dr. Devendra Singh", "MBBS, DCH (Pediatrics)", "pediatrics")],
    24: [("Dr. Nyay Bhai Gupta", "MBBS, MD (Pediatrics)", "pediatrics")],
    25: [("Dr. Asma Parveen", "MBBS, MD (Dermatology)", "dermatology")],
    26: [("Dr. Sanjeev Awasthi", "MBBS, MS (Orthopedics)", "orthopedic")],
    27: [("Dr. B. M. Agarwal", "MBBS, MD (Dermatology)", "dermatology")],
    28: [
        ("Dr. Gaurav Bhalla", "BDS, MDS (Dental Surgery)", "dental"),
        ("Dr. Dipti Jain Bhalla", "BDS, MDS (Dental Surgery)", "dental"),
    ],
    29: [("Dr. Masroor Ahmad", "MBBS (General Physician)", "general_physician")],
    30: [("Dr. Sanjay Singh", "MBBS, MD (Pediatrics)", "pediatrics")],
    31: [("Dr. Manas Shukla", "MBBS, MD (Pediatrics)", "pediatrics")],
}


def seed_lucknow(session: Session, reset: bool = False) -> None:
    if reset:
        reset_data(session)

    print("🌱 Seeding Lucknow healthcare data...")

    specialties = seed_specialties(session)
    languages = seed_languages(session)

    verified_at = datetime(2025, 1, 15, tzinfo=timezone.utc)
    provider_objects: list[Provider] = []

    for idx, (name, ptype, address, lat, lng, phone, hours_pattern, walk_in) in enumerate(
        LUCKNOW_PROVIDERS
    ):
        location_wkt = f"POINT({lng} {lat})"
        provider = Provider(
            id=uuid.uuid4(),
            name=name,
            type=ptype,
            address=address,
            city="Lucknow",
            location=f"SRID=4326;{location_wkt}",
            phone=phone,
            whatsapp=phone,
            opening_hours=build_opening_hours(hours_pattern),
            timezone="Asia/Kolkata",
            registration_number=f"UPMC-LKO-{2020 + idx:04d}",
            verification_status="verified",
            last_verified_at=verified_at,
            walk_in_available=walk_in,
            is_dummy=False,
        )
        session.add(provider)
        provider_objects.append(provider)

    session.flush()

    all_doctors: list[Doctor] = []
    for prov_idx, doctor_list in LUCKNOW_DOCTORS_BY_PROVIDER.items():
        provider = provider_objects[prov_idx]
        for doc_name, qualifications, specialty_slug in doctor_list:
            doctor = Doctor(
                id=uuid.uuid4(),
                provider_id=provider.id,
                full_name=doc_name,
                qualifications=qualifications,
                specialty_id=specialties[specialty_slug].id,
                is_dummy=False,
            )
            session.add(doctor)
            all_doctors.append(doctor)

    session.flush()

    # Assign Hindi (native) and English (fluent) to all Lucknow doctors
    for doctor in all_doctors:
        for lang_code, proficiency in [("hi", "native"), ("en", "fluent")]:
            if lang_code in languages:
                session.add(
                    DoctorLanguage(
                        doctor_id=doctor.id,
                        language_id=languages[lang_code].id,
                        proficiency=proficiency,
                    )
                )

    session.flush()

    # Seed services for each provider
    for idx, (_name, ptype, *_rest) in enumerate(LUCKNOW_PROVIDERS):
        provider = provider_objects[idx]
        if ptype == "hospital":
            service_list = HOSPITAL_SERVICES
        elif ptype == "clinic":
            docs = LUCKNOW_DOCTORS_BY_PROVIDER.get(idx, [])
            primary_spec = docs[0][2] if docs else "general_physician"
            service_list = SPECIALTY_SERVICES.get(primary_spec, CLINIC_SERVICES)
        else:
            docs = LUCKNOW_DOCTORS_BY_PROVIDER.get(idx, [])
            primary_spec = docs[0][2] if docs else "general_physician"
            service_list = SPECIALTY_SERVICES.get(primary_spec, CLINIC_SERVICES)

        for svc_name, price_min, price_max in service_list:
            session.add(
                Service(
                    id=uuid.uuid4(),
                    provider_id=provider.id,
                    name=svc_name,
                    price_min=price_min,
                    price_max=price_max,
                    currency="INR",
                    last_verified_at=verified_at,
                )
            )

    session.commit()
    print(
        f"✅ Seeded {len(provider_objects)} Lucknow providers and {len(all_doctors)} real doctors."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="TravelDoc Lucknow seed script")
    parser.add_argument(
        "--reset", action="store_true", help="Wipe existing data before seeding"
    )
    args = parser.parse_args()

    engine = get_sync_engine()
    with Session(engine) as session:
        seed_lucknow(session, reset=args.reset)


if __name__ == "__main__":
    main()
