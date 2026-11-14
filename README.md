# TravelDoc (working title)

**Find a trusted, language-matched doctor with clear costs, in minutes, in any unfamiliar city.**

> Status: Idea → Prototype planning
> Category: Travel × Health-tech

---

## 1. The Problem

International travelers and domestic tourists from other states who fall ill in an unfamiliar city don't know:

- **Which** hospital or clinic to trust
- **Whether** the doctor speaks their language (or a common one like English)
- **What** the treatment will cost before they walk in
- **How far** the nearest suitable option is, and whether it is open right now

Today they rely on hotel front desks, random Google Maps results, or insurance helplines. These are slow, inconsistent, and rarely show prices or verified language ability.

## 2. The Idea

An **Uber-style matching platform for medical care**. A traveler shares their location, preferred language, and a short description of what's wrong. The platform instantly returns a ranked list of **verified nearby doctors and clinics** with:

- Verified languages spoken
- Price range for common services
- Distance and travel time
- Open-now / walk-in availability
- Ratings from verified visits

One tap to call, WhatsApp, book, or get directions.

> **We are a directory and connector, not a medical provider.** We do not diagnose, treat, or give medical advice.

### How it differs from Uber

Uber matches a rider to a driver who is live right now. Doctors aren't "online" in that way, so matching here is based on **clinic hours, walk-in availability, and appointment slots**, not live GPS tracking. Real-time request/accept flows are layered on later.

## 3. Target Users

| Actor | Who | What they need |
|---|---|---|
| **Traveler** | International tourists, out-of-state domestic tourists, business travelers | Fast, trustworthy, language-matched care with known costs |
| **Provider** | Clinics, hospitals, independent doctors | Tourist patients, easy profile and price management |
| **Admin** | Our ops team | Verification, moderation, monitoring |
| **Partner** *(later)* | Hotels, hostels, tour operators, insurers | A guest-safety amenity or a local care network |

## 4. Initial Prototype (MVP) Scope

**Principle:** prove that travelers use it and providers keep it accurate, before building anything heavy.

**Launch scope:** one city, English + 1-2 other languages, no payments.

### 4.1 What we WILL build

**Traveler PWA (mobile-first website)**
- [ ] Location detection (GPS) with manual fallback
- [ ] Language selection and need input (symptom category or short free text)
- [ ] Ranked results list with map view
- [ ] Provider profile: languages, specialties, price ranges, verification badge, hours
- [ ] One-tap call / WhatsApp / directions
- [ ] Post-visit rating and "actual amount paid" capture
- [ ] Emergency banner with the local emergency number
- [ ] Minimal sign-up (no login for first search, phone OTP only when needed)

**Backend**
- [ ] Provider, doctor, services/prices, languages, requests, and reviews data model
- [ ] Geo-search (PostgreSQL + PostGIS)
- [ ] **Rule-based matching engine** scoring on distance, language match, open-now, specialty fit, verification, and rating
- [ ] REST API
- [ ] Basic notification to providers (WhatsApp or SMS) on new requests

**Provider side (lightweight)**
- [ ] Simple dashboard or form to update hours, languages, doctors on duty, and prices
- [ ] WhatsApp/form fallback for clinics that won't use a dashboard

**Admin console (minimal)**
- [ ] Provider onboarding and verification queue
- [ ] Review moderation
- [ ] Request monitoring, with manual reassignment

**Supply (not code, but critical)**
- [ ] 15-30 manually verified providers in the launch city
- [ ] Verification checklist: registration check, language confirmation call, facility check, published price ranges

### 4.2 What we will NOT build yet

- Native mobile apps
- Payments and insurance claims
- Telemedicine
- Ambulance / emergency dispatch
- ML-based ranking
- Multi-city tooling
- Microservices

### 4.3 Prototype success criteria

| Metric | Target (initial) |
|---|---|
| Median time from request to a matched result | under 1 minute |
| Providers who keep prices and hours updated | most of the network |
| Quoted vs. actual price accuracy | high and improving |
| Repeat or referral use | measurable from pilot partners |
| Active distribution partners (hotels/hostels) | several promoting actively |

## 5. Tech Stack (proposed)

| Layer | Choice |
|---|---|
| Frontend | Next.js / React (PWA), Tailwind |
| Backend | FastAPI (Python) or Node.js |
| Database | PostgreSQL + PostGIS |
| Cache / real-time (later) | Redis, WebSockets |
| Maps | Google Maps Platform or Mapbox |
| Messaging | WhatsApp Business API, Twilio, Firebase push |
| Auth | Phone OTP (Firebase Auth / Auth0) |
| AI (later) | LLM API for translation and symptom summaries |
| Hosting | Vercel / AWS / GCP + managed Postgres |

**Architecture:** a modular monolith. Split into services only when a part genuinely needs independent scaling.

## 6. Roadmap

| Phase | Focus | Timeline |
|---|---|---|
| 0 | Validate the problem (20-30 interviews, competitor map) | Weeks 1-3 |
| 1 | Pick a narrow wedge (one city, one segment, one promise) | Weeks 3-5 |
| 2 | Build the verified provider network | Weeks 4-8 |
| 3 | Concierge MVP (WhatsApp + landing page) | Weeks 5-10 |
| 4 | Prototype build and pilot with hotel/hostel partners | Weeks 8-16 |
| 5 | Business model and early traction | Months 4-8 |
| 6 | Choose the exit path | Months 6-12 |

**Build order for the prototype:** data model → matching engine → traveler PWA → provider side → real-time requests → language layer → admin console → city beta.

## 7. Business Model (to be tested)

- **B2B subscription:** hotels and hostels offer it as a guest-safety amenity (test first)
- **Insurer / assistance partnerships:** they need local verified networks
- **Provider referral fees:** only where legal and ethical
- **Premium traveler tier:** priority response and follow-up coordination

## 8. End Goal

The prototype exists to produce **proof and assets**, which support any of three outcomes:

1. **Build it into a startup.** Raise pre-seed funding on traction, then expand city by city with a repeatable playbook.
2. **Link it to a founder.** Hand over a package (pitch deck, validation report, pilot data, working prototype) for a co-founder or equity-based arrangement.
3. **Sell it.** The valuable assets are the **verified provider network, price database, traction data, brand, and distribution partnerships**. Likely buyers: travel insurers and assistance companies, online travel agencies, hotel-tech platforms, health-tech platforms, hospital chains, and medical-tourism facilitators.

## 9. Key Risks

- **Liability and trust:** one bad referral damages credibility. Verification and clear disclaimers are essential.
- **Regulation:** healthcare advertising and referral-fee rules vary by region. Get legal advice before taking commissions.
- **Privacy:** health data is sensitive. Minimize collection, encrypt it, and comply with DPDP (India) and GDPR (EU travelers).
- **Low-frequency use:** people need this rarely, so distribution via hotels, insurers, and partners matters more than direct marketing.
- **Stale data:** prices and hours drift, so periodic re-verification is built into the workflow.

## 10. Repository Structure (proposed)

```
/
├── apps/
│   ├── web/            # Traveler PWA
│   └── admin/          # Admin console
├── services/
│   └── api/            # Backend (matching, providers, requests)
├── db/
│   └── migrations/     # Schema and PostGIS setup
├── docs/
│   ├── research/       # Interviews, competitor analysis
│   └── verification/   # Provider verification checklist
└── README.md
```

## 11. Disclaimer

This platform connects travelers with independent healthcare providers. It does **not** provide medical advice, diagnosis, or treatment. In a life-threatening emergency, call your local emergency number immediately.
