# TravelDoc — Progress Report & Testing Guide

> **Project:** TravelDoc (Phase 1 Prototype)  
> **Status:** Phase 1 Complete (All Checkpoints 1 through 6 Delivered)  
> **Date:** November 20, 2026

---

## 1. Executive Summary & Progress

All required scope items for Phase 1 have been implemented, tested, and verified:

| Component | Status | Details |
|---|---|---|
| **Checkpoint 1: Architecture & Schema** | ✅ Completed | Monorepo layout, ERD, database tables with PostGIS geography, matching engine formula |
| **Checkpoint 2: Database, Migrations & Seed Data** | ✅ Completed | Alembic migrations, 30 dummy providers across Goa, ~65 doctors, 7 languages, 8 specialties, services with realistic price ranges in INR, 20 approved reviews, CSV importer tool (`import_csv.py`), and documentation |
| **Checkpoint 3: Matching Engine & API** | ✅ Completed | Pure rule-based scoring engine in `engine.py`, configurable `weights.yaml`, all 6 FastAPI endpoints (`/health`, `/config`, `/search`, `/providers/{id}`, `/reviews`, `/events`), 36 passing unit tests |
| **Checkpoint 4: Screen 1 (Search) & Screen 2 (Results)** | ✅ Completed | Mobile-first Next.js 14 PWA with GPS auto-detection, fallback area dropdown, language selector, care need chips, ranked provider cards, and List / Leaflet Map toggle |
| **Checkpoint 5: Screen 3 (Profile), Feedback & Admin** | ✅ Completed | Provider profile, opening hours with today highlighted, doctors and languages, upfront price table, sticky CTA bar (Call, WhatsApp, Directions), post-visit feedback modal, session analytics, and SQLAdmin interface |
| **Checkpoint 6: PWA Polish & Documentation** | ✅ Completed | PWA `manifest.json`, Service Worker (`sw.js`), `/offline` fallback page, `Makefile`, `README.md`, and test suite passing |

---

## 2. How to Start the App

### Option A: One-Command Setup with Docker Compose (Recommended)

1. **Prepare Environment Variables:**
   ```bash
   cp .env.example .env
   ```

2. **Start All Services (PostgreSQL + PostGIS, FastAPI, Next.js):**
   ```bash
   docker compose up --build -d
   ```

3. **Run Database Migrations:**
   ```bash
   docker compose exec api alembic upgrade head
   ```

4. **Seed the 30 Dummy Providers & Doctors:**
   ```bash
   docker compose exec api python -m db.seed --reset
   ```

5. **Access the Applications:**
   - **Frontend Mobile PWA:** [http://localhost:3000](http://localhost:3000)
   - **Interactive API Documentation (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Admin Panel:** [http://localhost:8000/admin](http://localhost:8000/admin)  
     *(Username: `admin` | Password: `changeme`)*

---

### Option B: Local Development Setup (Without Docker)

#### Backend (FastAPI):
```bash
# Navigate to services/api
cd services/api

# Install dependencies (requires Python 3.11)
pip install -e ".[dev]"

# Run tests
$env:PYTHONPATH="."; pytest -p no:deepeval tests/ -v

# Run the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend (Next.js):
```bash
# Navigate to apps/web
cd apps/web

# Install dependencies
npm install

# Run frontend development server
npm run dev
```

---

## 3. How to Test the Application

### 3.1 Automated Test Suite

Run the backend test suite (36 tests covering matching engine rules, edge cases, configuration, and API routes):

```bash
# Via Docker:
docker compose exec api pytest tests/ -v

# Or locally:
$env:PYTHONPATH="services/api"; pytest -p no:deepeval services/api/tests/ -v
```

**Test Suite Coverage Summary:**
- **Distance Scoring (`TestDistanceScore`):**
  - 0 km distance → score 1.0 (100%)
  - Halfway radius (5 km) → score 0.5 (50%)
  - Boundary distance (10 km) → score 0.0
  - Beyond radius (> 10 km) → clamped to 0.0
  - Negative distance → clamped to 0.0
- **Language Scoring (`TestLanguageScore`):**
  - Exact requested language match → 1.0
  - Case-insensitive matching → 1.0
  - English fallback when requested language unavailable → 0.7
  - No match and no English → 0.0
- **Opening Hours & Walk-in (`TestOpenNowScore`):**
  - 24x7 flag → 1.0
  - Scheduled hours active → 1.0
  - Closed per schedule but walk-in available → 0.5
  - Closed without walk-in → 0.0
- **Specialty Mapping (`TestSpecialtyScore`):**
  - Need-to-specialty match (e.g., child health → pediatrics) → 1.0
  - General physician fallback → 0.5
  - Non-matching specialty → 0.0
- **Verification & Rating:**
  - `verified` (1.0) vs `pending` (0.3) vs `rejected` (0.0)
  - Rating normalization (5 stars → 1.0, 4 stars → 0.8, no ratings default → 0.5)
- **API Endpoints:**
  - `GET /health` → 200 OK
  - Weights configuration validation (sum to 1.0)
  - `POST /search` validation for invalid need categories & out-of-bounds coordinates
  - `POST /reviews` rating range validation (1–5)
  - `POST /events` analytics payload validation

---

### 3.2 Manual End-to-End Walkthrough

1. **Screen 1: Search (`/`)**
   - Open [http://localhost:3000](http://localhost:3000) on a mobile-sized viewport (e.g. Chrome DevTools Responsive Mode, 390px width).
   - Check that the top red emergency banner displays `"Life-threatening emergency? Call 112 immediately"`.
   - Check the demo disclaimer banner (`"Demo Prototype: Doctors, prices, and reviews shown are placeholders"`).
   - Select your spoken language (e.g., Russian, French, or English). Preference is saved in `localStorage`.
   - Use GPS auto-detect or pick a location (e.g. Panaji, Calangute, Baga).
   - Click a care category chip (e.g. *Fever / Flu* or *Injury / Wound*).
   - Tap **"Find doctors near me"**.

2. **Screen 2: Search Results (`/results`)**
   - Verify ranked cards show: provider name, distance (km), open-now status, verification badge, price range for the need, and match reasons (e.g. `"Speaks Russian"`, `"Open now"`).
   - Toggle to **Map View** and click on any pin to view the popup.
   - Tap any provider card to open their profile.

3. **Screen 3: Provider Profile (`/providers/{id}`)**
   - Check full details: address, opening schedule with **Today** highlighted, list of doctors and the languages they speak, and the upfront price table.
   - Test the sticky bottom bar:
     - **Call:** Opens `tel:+91...`
     - **WhatsApp:** Opens `wa.me/...` with pre-filled message
     - **Directions:** Opens Google Maps navigation link
   - Tap **"Leave visit feedback"** to test the feedback form:
     - Select a star rating (1–5)
     - Enter an actual amount paid (e.g. `500`)
     - Enter an optional comment and submit
     - Confirm the success message displays and the review is logged as `pending` in the database.

4. **Admin Panel (`/admin`)**
   - Navigate to [http://localhost:8000/admin](http://localhost:8000/admin).
   - Log in with `admin` / `changeme`.
   - Verify you can view and edit:
     - **Providers:** Filter by `is_dummy` and `verification_status`.
     - **Reviews:** Approve or hide submitted patient feedback.
     - **Analytics Events:** Inspect logged events (`search_submitted`, `call_tapped`, etc.).

---

## 4. How to Import Real Data

When ready to transition from dummy data to production data:

1. Format your records following [`docs/data-format.md`](docs/data-format.md).
2. Run the CSV importer:
   ```bash
   docker compose exec api python -m db.import_csv /app/db/seed/providers.csv
   docker compose exec api python -m db.import_csv /app/db/seed/doctors.csv
   docker compose exec api python -m db.import_csv /app/db/seed/services.csv
   ```
3. Delete the dummy data records:
   ```sql
   DELETE FROM doctors WHERE is_dummy = true;
   DELETE FROM providers WHERE is_dummy = true;
   ```
4. Set `IS_DEMO_DATA=false` in `.env`.
