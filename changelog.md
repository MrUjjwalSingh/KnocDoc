# TravelDoc Changelog

> **Project:** TravelDoc (Phase 1 Prototype)
> **Status:** Phase 1.1 Complete
> **Date:** November 22, 2026

---

## 1. Executive Summary & Progress

All required scope items for Phase 1 have been implemented, tested, and verified:

| Component | Status | Details |
|---|---|---|
| **Checkpoint 1: Architecture & Schema** | Completed | Monorepo layout, ERD, database tables with PostGIS geography, matching engine formula |
| **Checkpoint 2: Database, Migrations & Seed Data** | Completed | Alembic migrations, 30 dummy providers, 52 doctors, 7 languages, 8 specialties, price ranges, 20 approved reviews, CSV importer, and documentation |
| **Checkpoint 3: Matching Engine & API** | Completed | Rule-based scoring, configurable weights, and all FastAPI endpoints |
| **Checkpoint 4: Search and Results** | Completed | Mobile-first Next.js PWA with GPS, language, category, provider cards, and Leaflet map |
| **Checkpoint 5: Profile, Feedback & Admin** | Completed | Provider profiles, prices, actions, moderated feedback, analytics, and SQLAdmin |
| **Checkpoint 6: PWA Polish & Documentation** | Completed | Manifest, service worker, offline page, Makefile, README, and test suite |

---

## Phase 1.1 - Docker and Runtime Fixes

- Shortened API Docker setup and pinned backend/dev package versions.
- Fixed CORS parsing, Alembic enum creation, Next.js server-side API routing, and PostCSS startup.
- Added `happy-dom` and excluded host `node_modules`/`.next` files from the web Docker context.
- Rebuilt and verified the API, web, database, migration, search, provider profiles, and routes.
- Verification: 36 backend tests and 1 frontend test pass.
