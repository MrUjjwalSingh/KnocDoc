# TravelDoc — CSV Data Format

This document describes the CSV format for importing real provider data to replace the dummy seed data.

> **Important**: All records imported via CSV will have `is_dummy = false` automatically.
> Dummy data (`is_dummy = true`) can be deleted after import with:
> ```sql
> DELETE FROM doctors WHERE is_dummy = true;
> DELETE FROM providers WHERE is_dummy = true;
> ```

---

## providers.csv

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `name` | string | ✅ | Provider/clinic name |
| `type` | enum | ✅ | `clinic`, `hospital`, or `independent_doctor` |
| `address` | string | ✅ | Full street address |
| `city` | string | ✅ | City name |
| `lat` | float | ✅ | Latitude (decimal degrees) |
| `lng` | float | ✅ | Longitude (decimal degrees) |
| `phone` | string | | Phone number with country code (e.g. +919876543210) |
| `whatsapp` | string | | WhatsApp number with country code |
| `hours_24x7` | boolean | | `true` for 24x7, otherwise use the opening_hours JSON column |
| `timezone` | string | | IANA timezone (default: `Asia/Kolkata`) |
| `registration_number` | string | | Medical council registration |
| `verification_status` | enum | | `verified`, `pending`, or `rejected` (default: `pending`) |
| `walk_in_available` | boolean | | `true` or `false` (default: `true`) |

**Example:**
```csv
name,type,address,city,lat,lng,phone,whatsapp,hours_24x7,verification_status,walk_in_available
"City Medical Clinic",clinic,"123 MG Road, Panaji",Goa,15.4909,73.8278,+919876543210,+919876543210,false,verified,true
```

---

## doctors.csv

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `provider_id` | UUID | ✅ | UUID of the provider (from providers table) |
| `full_name` | string | ✅ | Doctor's full name |
| `qualifications` | string | | Degrees and certifications (e.g. MBBS, MD) |
| `specialty_slug` | enum | | One of: `general_physician`, `pediatrics`, `dental`, `orthopedic`, `emergency_care`, `dermatology`, `gastroenterology`, `ent` |

**Example:**
```csv
provider_id,full_name,qualifications,specialty_slug
"550e8400-e29b-41d4-a716-446655440000","Dr. Anjali Patel","MBBS, MD (General Medicine)",general_physician
```

---

## services.csv

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `provider_id` | UUID | ✅ | UUID of the provider |
| `name` | enum | ✅ | Service name: `general_consultation`, `xray`, `stitches`, `dental_checkup`, `basic_blood_test`, `fever_treatment`, `stomach_issue_treatment`, `minor_injury_dressing`, `emergency_care` |
| `price_min` | float | | Minimum price in local currency |
| `price_max` | float | | Maximum price in local currency |
| `currency` | string | | Currency code (default: `INR`) |

**Example:**
```csv
provider_id,name,price_min,price_max,currency
"550e8400-e29b-41d4-a716-446655440000",general_consultation,400,900,INR
```

---

## Workflow: Replacing Dummy Data

1. Export your real provider data into the three CSVs above.
2. Run the import scripts inside the API container:
   ```bash
   docker compose exec api python -m db.import_csv /path/to/providers.csv
   docker compose exec api python -m db.import_csv /path/to/doctors.csv
   docker compose exec api python -m db.import_csv /path/to/services.csv
   ```
3. Remove dummy data:
   ```sql
   DELETE FROM doctor_languages WHERE doctor_id IN (SELECT id FROM doctors WHERE is_dummy = true);
   DELETE FROM services WHERE provider_id IN (SELECT id FROM providers WHERE is_dummy = true);
   DELETE FROM reviews WHERE provider_id IN (SELECT id FROM providers WHERE is_dummy = true);
   DELETE FROM doctors WHERE is_dummy = true;
   DELETE FROM providers WHERE is_dummy = true;
   ```
4. Set `IS_DEMO_DATA=false` in your `.env` file.
5. Restart the API: `docker compose restart api`

---

## Tuning the Matching Engine

Edit `services/api/app/matching/weights.yaml` to adjust scoring weights and need→specialty mappings. No code changes required. Restart the API after editing.

```yaml
weights:
  distance: 0.30   # Increase to prioritize closer providers
  language: 0.25   # Increase if language match is critical
  open_now: 0.20
  specialty: 0.15
  verification: 0.05
  rating: 0.05
```
