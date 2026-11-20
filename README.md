# TravelDoc (Phase 1 Prototype)

> **Find a trusted, language-matched doctor with clear costs, in minutes, in any unfamiliar city.**
> A medical directory and connector for travelers. We do NOT diagnose, treat, or give medical advice.

---

## 1. Architecture Overview

```
                      ┌───────────────────────────────────────┐
                      │    Mobile-First PWA (Next.js 14)      │
                      │  Screen 1: Search (GPS/City Pick)     │
                      │  Screen 2: Results (List + Leaflet)   │
                      │  Screen 3: Profile + Feedback CTA     │
                      └──────────────────┬────────────────────┘
                                         │ JSON / REST
                                         ▼
                      ┌───────────────────────────────────────┐
                      │         FastAPI Backend               │
                      │  • GET /config (city, emergency #)    │
                      │  • POST /search (matching engine)     │
                      │  • GET /providers/{id} (full profile) │
                      │  • POST /reviews (moderated feedback) │
                      │  • POST /events (anonymous analytics) │
                      │  • /admin (SQLAdmin auth portal)      │
                      └──────────────────┬────────────────────┘
                                         │ SQLAlchemy 2.0 (Async)
                                         ▼
                      ┌───────────────────────────────────────┐
                      │     PostgreSQL 16 + PostGIS           │
                      │  • providers (GiST location index)    │
                      │  • doctors, specialties, languages    │
                      │  • services & prices, reviews, events │
                      └───────────────────────────────────────┘
```

---

## 2. Quickstart (Under 5 Commands)

```bash
# 1. Copy environment variables
cp .env.example .env

# 2. Start services (PostgreSQL PostGIS + FastAPI + Next.js)
docker compose up --build -d

# 3. Apply database migrations
docker compose exec api alembic upgrade head

# 4. Seed dummy data (30 providers, 65+ doctors in Goa, India)
docker compose exec api python -m db.seed --reset

# 5. Open the app in your browser:
#    - Web PWA:   http://localhost:3000
#    - API Docs:  http://localhost:8000/docs
#    - Admin:     http://localhost:8000/admin (User: admin / Pass: changeme)
```

---

## 3. Matching Engine & Weight Tuning

The rule-based matching engine scores providers from **0 to 100**:

$$\text{Score} = 100 \times (0.30 \times \text{distance} + 0.25 \times \text{language} + 0.20 \times \text{open\_now} + 0.15 \times \text{specialty} + 0.05 \times \text{verification} + 0.05 \times \text{rating})$$

| Component | Weight | Logic |
|---|---|---|
| **Distance** | 30% | $\max(0, 1 - \frac{\text{distance\_km}}{\text{max\_radius\_km}})$ via PostGIS `ST_DWithin` / `ST_Distance` |
| **Language** | 25% | 1.0 if doctor speaks requested language, 0.7 if English fallback, 0.0 otherwise |
| **Open Now** | 20% | 1.0 if open now (or 24x7), 0.5 if closed but walk-in available, 0.0 otherwise |
| **Specialty** | 15% | 1.0 for mapped specialty, 0.5 for general physician fallback, 0.0 otherwise |
| **Verification** | 5% | 1.0 for `verified`, 0.3 for `pending`, 0.0 for `rejected` |
| **Rating** | 5% | Average approved review rating / 5.0 (default 0.5 if no ratings) |

### Tuning Weights Without Code Changes
All weights and need-to-specialty mappings are stored in:
`services/api/app/matching/weights.yaml`

Simply edit the numbers in `weights.yaml` and restart the API container:
```bash
docker compose restart api
```

---

## 4. Replacing Dummy Data With Real Data

All seeded dummy data has `is_dummy = true`. To import real data:

1. Prepare your data in the CSV formats documented in [`docs/data-format.md`](docs/data-format.md).
2. Run the CSV import tool:
   ```bash
   docker compose exec api python -m db.import_csv /app/db/seed/providers.csv
   docker compose exec api python -m db.import_csv /app/db/seed/doctors.csv
   docker compose exec api python -m db.import_csv /app/db/seed/services.csv
   ```
3. Remove the placeholder dummy records:
   ```sql
   DELETE FROM doctor_languages WHERE doctor_id IN (SELECT id FROM doctors WHERE is_dummy = true);
   DELETE FROM services WHERE provider_id IN (SELECT id FROM providers WHERE is_dummy = true);
   DELETE FROM reviews WHERE provider_id IN (SELECT id FROM providers WHERE is_dummy = true);
   DELETE FROM doctors WHERE is_dummy = true;
   DELETE FROM providers WHERE is_dummy = true;
   ```
4. Set `IS_DEMO_DATA=false` in `.env` and restart.

---

## 5. API Endpoints

- `GET /health` — Health and version check
- `GET /config` — City name, center coordinates, emergency phone, supported languages, and need categories
- `POST /search` — Match and rank providers:
  ```json
  { "lat": 15.4909, "lng": 73.8278, "language_code": "ru", "need_category": "fever" }
  ```
- `GET /providers/{id}` — Full provider profile (doctors, schedules, price ranges, verification badge)
- `POST /reviews` — Submit post-visit feedback (moderated as `pending`)
- `POST /events` — Anonymous session event logging (`search_submitted`, `provider_opened`, `call_tapped`, etc.)
- `GET /admin` — SQLAdmin management interface (basic auth)

---

## 6. Development & Testing

```bash
# Run backend pytest suite (matching engine + API validation)
make test-api
# or locally:
$env:PYTHONPATH="services/api"; pytest -p no:deepeval services/api/tests/ -v

# Run frontend vitest
make test-web

# Linting
make lint
```

---

## 7. License & Disclaimer
This software is provided for directory connection purposes only. It is not intended to provide medical advice, diagnosis, or treatment.
