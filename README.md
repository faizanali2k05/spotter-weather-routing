# Spotter Weather-Aware Truck Routing

A production-ready, full-stack dispatch advisory system that calculates alternative commercial driving routes, samples spatial checkpoints at uniform distance intervals, retrieves time-aligned Open-Meteo forecasts, evaluates load-dependent weather safety rules, and renders an interactive geospatial route comparison and spatial weather heatmap.

---

## 🚀 Key Highlights & Architectural Improvements

- **Resilient Multi-Provider Geocoding:** OpenStreetMap Nominatim primary geocoding with automatic, instant fallback to Open-Meteo Geocoding API if rate limits or HTTP errors occur.
- **Deduplicated Multi-Alternative Routing:** Pluggable `RoutingProvider` abstraction with OSRM driving engine; deduplicates redundant routes within 1.5% distance/duration variance.
- **Commercial Truck Adapter:** Architectural adapter (`CommercialTruckRoutingProviderAdapter`) for enterprise truck telematics (axle weights, low-clearance bridges, hazmat classifications).
- **Batched & Cached Weather Engine:** Batches up to 30 coordinates into single Open-Meteo queries; eliminates previous sequential HTTP calls; in-memory TTL caching (15 mins).
- **Accurate Unit Precision:** Queries Open-Meteo with `wind_speed_unit=mph` and `precipitation_unit=inch`; fixed previous snowfall double-conversion bug.
- **Deterministic Risk Engine:** Exact boundary evaluation for Wind, Rain, Snow, and load-dependent trucking rules (>30k lbs and >40k lbs modifiers).
- **Multi-Dimensional Route Ranking:** Prioritizes No-Travel-free paths, lowest severe exposure, lowest high exposure, lowest distance-weighted average risk, and duration.
- **Real Spatial Weather Heatmap (Phase 7):** Spatially samples an atmospheric grid across the travel corridor; precomputes 17 temporal frames; renders continuous, hardware-accelerated MapLibre GL `heatmap` layers driven by an interactive 0–48 hour timeline slider.
- **Production-Grade Error Handling:** Replaced catch-all exception masking with typed exceptions returning standardized JSON error schemas (`400`, `404`, `429`, `502`, `504`).
- **Modern Modular React 18 / TypeScript UI:** Rebuilt monolithic code into clean feature modules (`components/`, `features/`, `services/`, `hooks/`, `types/`).

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, MapLibre GL, Lucide React |
| **Backend** | Python 3.12+, Django 5.2, Django REST Framework, WhiteNoise, Gunicorn |
| **Routing** | OSRM (Open Source Routing Machine) public engine + Truck Adapter |
| **Geocoding** | OpenStreetMap Nominatim + Open-Meteo Geocoding Fallback |
| **Weather** | Open-Meteo Numerical Forecast API (batched, hourly, UTC-aligned) |
| **Testing** | Pytest, Pytest-Django, Requests Mock, DRF Test Client (45 tests) |
| **Deployment** | Render (Docker Backend), Vercel (Edge Frontend) |

---

## 🚦 Weather Risk Thresholds & Load Rules

### Atmospheric Thresholds
- **Wind (mph):** Low `< 25` · Moderate `25–34` · High `35–44` · Severe `45–54` · No Travel `≥ 55`
- **Rain (in/hr):** Low `< 0.10` · Moderate `0.10–0.24` · High `0.25–0.49` · Severe `0.50–1.00` · No Travel `> 1.00`
- **Snow (in/hr):** Low `< 0.50` · Moderate `0.50–0.99` · High `1.00–1.99` · Severe `2.00–3.00` · No Travel `> 3.00`

### Load-Dependent Modifiers
- **Wind 45–54 mph and cargo load > 30,000 lbs:** Elevated to **No Travel**
- **Wind 35–44 mph and cargo load > 40,000 lbs:** Elevated to **Severe**

### Safety Ranking Hierarchy
1. Routes free of No Travel conditions
2. Lowest Severe hazard mileage
3. Lowest High hazard mileage
4. Lowest distance-weighted average risk index
5. Driving duration in minutes
6. Total distance in miles

> ⚠️ **No Safe Route Notice:** If all available routes encounter No Travel hazards, the system suspends recommendation, displays a prominent red warning banner, and advises delaying dispatch.

---

## ⚡ Quickstart Local Setup

### 1. Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver 127.0.0.1:8000
```
Verify health: [http://127.0.0.1:8000/api/health/](http://127.0.0.1:8000/api/health/)

### 2. Frontend Setup (Separate Terminal)
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Open application: [http://localhost:5173](http://localhost:5173)

---

## 🧪 Automated Testing

### Backend Unit & Integration Tests (100% Offline / Deterministic)
```bash
.venv/bin/pytest backend/tests
```
Expected output:
```
======================== 44 passed, 1 skipped in ~1.9s =========================
```

### Optional Live External Provider Smoke Test
```bash
RUN_LIVE_TESTS=1 .venv/bin/pytest backend/tests/test_live_smoke.py
```

### Frontend Build & Typecheck
```bash
cd frontend
npm run build
```

---

## 📡 API Reference Summary

- `GET /api/health/`: Service health check, version, and provider status.
- `GET /api/geocode/?q={location}`: Geocode place query with automatic fallback.
- `POST /api/plan/`: Route calculation, checkpoints, weather risk, ranking, and corridor heatmap.

### Example Plan Request:
```json
{
  "origin": "New York, NY",
  "destination": "Philadelphia, PA",
  "departure": "2026-10-18T14:00:00Z",
  "load_lbs": 35000,
  "spacing_miles": 25
}
```

Detailed schemas and error responses are documented in [docs/API.md](docs/API.md).

---

## 🚢 Deployment

- **Backend (Render):** Automatically built via `backend/Dockerfile` using `render.yaml`. Configured with Gunicorn, WhiteNoise, and health check path `/api/health/`.
- **Frontend (Vercel):** Deployed with Vite framework preset, root directory `frontend`, build command `npm run build`, and `VITE_API_BASE_URL` pointing to the Render backend.

Detailed deployment instructions are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## 📚 Documentation Index

- [docs/AUDIT.md](docs/AUDIT.md) — Comprehensive repository audit, root-cause analyses, and prioritized remediation.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — System architecture, module design, and sequence diagrams.
- [docs/API.md](docs/API.md) — Complete endpoint reference, schemas, and error codes.
- [docs/LOCAL_SETUP.md](docs/LOCAL_SETUP.md) — Step-by-step local development setup.
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Production deployment guide for Render & Vercel.
- [docs/TESTING.md](docs/TESTING.md) — Automated test suite structure, coverage, and test running guide.
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — Common error resolutions (CORS, 502/503, Docker build).
- [docs/ASSESSMENT_CHECKLIST.md](docs/ASSESSMENT_CHECKLIST.md) — Verification checklist against all assessment criteria.
- [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) — Provider boundaries, OSRM public demo constraints, and future work.

---

## 🎥 5–10 Minute Loom Demonstration Script

When presenting the project on Loom, follow this structured walkthrough:

1. **Introduction & System Overview (1 min):**
   - Introduce Spotter Weather-Aware Truck Routing.
   - Explain the core challenge: commercial trucking routes exposed to severe wind gusts, heavy rainfall, and blizzard conditions.
2. **Architecture & Key Fixes (1.5 min):**
   - Walk through the decoupled backend (`routing_provider.py`, `weather_service.py`, `risk.py`, `corridor_service.py`).
   - Mention the resolution of the historical blockers: Nominatim 403 & Open-Meteo 503 User-Agent fixes, snowfall unit division fix, CORS multi-origin regexes, and typed DRF exception handling.
3. **Trip Planning & Route Alternatives (1.5 min):**
   - In the live UI, plan a trip from *New York, NY* to *Philadelphia, PA* departing tomorrow with a 35,000 lb cargo load and 25-mile checkpoint intervals.
   - Show how the backend evaluates distinct OSRM route alternatives without phantom route fabrication.
4. **Interactive Map & Checkpoint Details (1.5 min):**
   - Click individual checkpoint markers along the route.
   - Show milestone distance, ETA in local time, wind speed, rain intensity, snow intensity, and contributing hazard factors.
5. **Spatial Corridor Weather Heatmap & 48-Hour Slider (1.5 min):**
   - Scrub the 0–48 hour timeline slider.
   - Demonstrate how the MapLibre GL spatial heatmap dynamically updates to show atmospheric risk intensity across the entire geographical corridor.
   - Explain the distinction between arrival-time waypoint exposure and corridor radar at a specific forecast hour.
6. **Load-Dependent Risk & No-Travel Safety Behavior (1.5 min):**
   - Explain the load-dependent wind rules (45–54 mph with >30k lbs => No Travel; 35–44 mph with >40k lbs => Severe).
   - Demonstrate what happens when conditions exceed No Travel thresholds: the system flags the route, removes safe recommendation, and issues an advisory alert.
7. **Automated Test Suite & Verification (1 min):**
   - Show terminal running `.venv/bin/pytest backend/tests` (44 passed).
   - Show `npm run build` compiling cleanly in 7 seconds.
   - Conclude with deployment readiness on Render and Vercel.
