# Spotter Weather-Aware Truck Routing — Repository Audit & Assessment

**Date:** October 2026  
**Auditor:** Principal Full-Stack / Geospatial Routing & DevOps Engineer  
**Scope:** Architecture, Backend (Django/DRF), Frontend (React/TypeScript/MapLibre), External Providers (OSRM, Open-Meteo, Nominatim), Security, Testing, and Deployment.

---

## 1. Executive Summary

The **Spotter Weather-Aware Truck Routing** application provides route planning, waypoint weather forecasting, risk classification, and interactive route visualization for commercial trucking. While the core algorithmic concept is well-conceived, an in-depth audit of the codebase revealed several critical blockers, architectural deficiencies, and unhandled failure modes that cause production failures, CORS errors, TypeScript build breakages, and inaccurate weather risk assessments.

This document details prioritized findings across 10 critical dimensions, provides root-cause analyses, and outlines the precise remediation plan implemented in this update.

---

## 2. Prioritized Findings

| Priority | Category | Finding | Impact | Status |
| :--- | :--- | :--- | :--- | :--- |
| **P0 (Blocker)** | Provider / Routing | Nominatim geocoder returned HTTP 403 Access Denied; Open-Meteo returned 503 Service Unavailable | Total service failure; app displays generic "Routing or weather provider unavailable" | Investigated & Solved |
| **P0 (Blocker)** | Frontend / Build | TypeScript compilation fails (`import.meta.env` missing Vite client types; MapLibre popup null reference) | Vercel and local `npm run build` fails | Fixed |
| **P0 (Blocker)** | Security / CORS | Inadequate CORS origins; `127.0.0.1:5173` and Vercel preview branches blocked | "Failed to fetch" / "CORS error" in browser | Fixed |
| **P1 (Critical)** | Weather Integration | Snowfall double-conversion bug (Open-Meteo `precipitation_unit=inch` divided by 2.54) | Snowfall severely underestimated (~39% of actual); incorrect risk levels | Fixed |
| **P1 (Critical)** | Architecture / API | Monolithic `main.tsx` (all UI/state/map/logic in 44 minified lines); no modular components | Unmaintainable, unreadable, brittle frontend | Rebuilt |
| **P1 (Critical)** | Heatmap Feature | Missing spatial weather heatmap (only rendered sparse route checkpoint circles; disclaimer stated no spatial heatmap) | Incomplete core assessment requirement | Implemented |
| **P1 (Critical)** | Error Handling | Catch-all `except Exception:` masked all provider, validation, and network errors into a single 502 message | Zero observability into actual root causes; inability to debug production | Rebuilt |
| **P2 (Major)** | Performance / Scaling | Open-Meteo queries issued sequentially in single-point calls per checkpoint without batching or persistent caching | Provider rate-limiting, slow response times (>10s for long routes) | Refactored with Batching & In-memory Cache |
| **P2 (Major)** | Routing Engine | Missing provider abstraction; no route deduplication; OSRM public demo limitation not formally abstracted | Risk of duplicate routes, lack of alternative provider extensibility | Refactored |
| **P2 (Major)** | Testing | Only 2 unit tests covering basic risk threshold math; zero tests for geocoding, routing, serializers, CORS, or frontend | Zero regression protection | Comprehensive Test Suite Added |
| **P3 (Minor)** | Repository Hygiene | Missing root `.gitignore`; untracked `.venv`, `__pycache__`, `db.sqlite3`, `node_modules` | Polluted repository state, accidental credential/build artifacts commit | Added |

---

## 3. Detailed Root Cause Analysis

### 3.1 Nominatim HTTP 403 & Open-Meteo 503 Failures
- **Root Cause:**
  1. OpenStreetMap Nominatim enforces a strict User-Agent policy that blocks generic or educational scrapers without identifiable application details or contact info.
  2. Open-Meteo drops or throttles requests originating from Python `requests` default User-Agent (`python-requests/2.32.x`) with HTTP 503 / 403.
  3. Single-coordinate queries were fired sequentially in a loop for every checkpoint. For a trip with 3 route alternatives of 20 checkpoints each, up to 60 sequential HTTP requests were triggered per plan invocation, exceeding rate limits and triggering provider timeouts.
- **Remediation:**
  - Configured custom, identifiable User-Agent headers across all outbound requests.
  - Added multi-geocoder fallback strategy: OSM Nominatim with immediate fallback to Open-Meteo Geocoding API (`https://geocoding-api.open-meteo.com/v1/search`), guaranteeing high availability.
  - Implemented multi-coordinate batch requests (`latitude=lat1,lat2&longitude=lon1,lon2`) supported natively by Open-Meteo.
  - Added request-level and TTL-based coordinate weather caching.

### 3.2 Frontend TypeScript Compilation Breakage
- **Root Cause:**
  - `frontend/tsconfig.json` lacked `"types": ["vite/client"]`, causing `import.meta.env` to fail type checking with `TS2339: Property 'env' does not exist on type 'ImportMeta'`.
  - In `clickPoint` (MapLibre event listener), map reference `m` was typed as `MLMap | null`, failing strict null checks when passed to `Popup.addTo(m)`.
- **Remediation:**
  - Added `vite-env.d.ts` and updated `tsconfig.json` with proper Vite client types.
  - Refactored map logic with non-null assertion or guard clauses and modularized React MapLibre integration.

### 3.3 CORS Configuration Failures
- **Root Cause:**
  - `backend/config/settings.py` only permitted `http://localhost:5173` by default. When the browser navigated to `http://127.0.0.1:5173` or a Vercel preview deployment (`https://spotter-weather-routing-*.vercel.app`), Django rejected the preflight OPTIONS request.
- **Remediation:**
  - Added localhost, 127.0.0.1 (ports 5173, 3000, 4173) to default dev origins.
  - Added regex support (`CORS_ALLOWED_ORIGIN_REGEXES = [r"^https:\/\/.*\.vercel\.app$"]`) to support Vercel preview and production deployments safely.
  - Ensured correct middleware order and explicit headers for preflight requests.

### 3.4 Snowfall Unit Double-Conversion
- **Root Cause:**
  - `services.py` requested `precipitation_unit=inch` from Open-Meteo. The Open-Meteo documentation confirms that when `precipitation_unit=inch`, `rain` is returned in inches and `snowfall` is returned in inches.
  - Line 67 of `services.py` executed: `round(float(hourly['snowfall'][i] or 0) / 2.54, 3)`. Dividing inches by 2.54 mistakenly treated the value as centimeters, reducing actual snowfall by ~61%.
- **Remediation:**
  - Corrected weather normalization: when requesting inches, use snowfall values directly without redundant unit division.

### 3.5 Missing True Spatial Heatmap
- **Root Cause:**
  - The previous code only rendered checkpoint points with circular blur rings along the route path and explicitly admitted in the UI: *"Forecast timeline highlights planned checkpoint arrivals; it does not generate a spatial forecast heatmap."*
  - Assessment Phase 7 explicitly requires:
    1. Geographic weather sampling around the route corridor.
    2. Spatially distributed risk values.
    3. Weather risk intensity visualization (MapLibre GL heatmap layer).
    4. 0–48 hour time slider that dynamically updates spatial weather conditions independent of vehicle travel time.
- **Remediation:**
  - Added corridor grid sampling around bounding boxes of routes.
  - Provided dedicated backend spatial weather sampling / corridor heatmap endpoint or plan payload.
  - Rendered a true MapLibre GL `heatmap` layer with dynamic weight and color ramps driven by the 0–48 hour forecast timeline.

### 3.6 Frontend Monolith Architecture
- **Root Cause:**
  - The entire UI was compacted into `main.tsx` (over 12,000 characters without line breaks or modularity). Components, forms, icons, map logic, and timeline controls were tightly coupled.
- **Remediation:**
  - Structured frontend into clean, maintainable feature modules:
    - `src/components/common/` (Header, Sidebar, MetricCard, ErrorBanner, Badges)
    - `src/features/routing/` (TripPlannerForm, RouteCard, RouteComparisonList)
    - `src/features/weather/` (WeatherTimelineSlider, WeatherSummaryPanel, HazardLegend)
    - `src/features/map/` (MapView, RouteLayers, CheckpointMarkers, HeatmapOverlay)
    - `src/services/` (API client with typed requests/responses)
    - `src/types/` (Domain types for Trip, Route, Weather, Risk, Heatmap)

---

## 4. Assessment Requirements Compliance Checklist

| Phase | Assessment Requirement | Pre-Audit Status | Target Post-Remediation Status |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Repository Audit (`docs/AUDIT.md`) | Missing | Complete |
| **Phase 2** | Fix CORS, Build, and Provider 502 Blocker | Broken | Complete & Verified |
| **Phase 3** | Rebuild Routing Engine & Deduplication | Inflexible (single hardcoded call) | Pluggable `RoutingProvider`, OSRM, deduplication |
| **Phase 4** | Weather Integration (Batching, Timezones, Units) | Buggy (snowfall /2.54, sequential N calls) | Batched, cached, accurate units & time horizons |
| **Phase 5** | Risk Engine (Exact Boundaries & Load Rules) | Basic | Fully verified against specification |
| **Phase 6** | Route Ranking (No Travel exclusion, explanations) | Minimal sort key without explanation | Multi-factor ranking with human explanations |
| **Phase 7** | Spatial Weather Heatmap & 0-48h Timeline | Not implemented (circles only) | Full MapLibre spatial heatmap + time slider |
| **Phase 8** | Complete Modern UI / UX Dashboard | Minified monolithic file | Modern modular React 18 + TS architecture |
| **Phase 9** | DRF API Validation & Documentation | Basic ad-hoc JSON check | DRF Serializers, validation, standard error schemas |
| **Phase 10** | Automated Test Suite | 2 tests | Full backend + frontend unit and integration tests |
| **Phase 11** | End-to-End Testing & Verification | None | Live scenario verification |
| **Phase 12** | Docker & Deployment Readiness | Brittle build | Hardened Dockerfile, Render & Vercel parity |
| **Phase 13** | Documentation Suite | Only basic README | Complete `docs/` documentation suite |

