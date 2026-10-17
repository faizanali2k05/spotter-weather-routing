# Spotter Weather-Aware Truck Routing — Testing Documentation

This document describes the testing strategy, test structure, coverage areas, and execution instructions for the automated test suite.

---

## 1. Test Architecture & Design Principles

The automated test suite follows these core principles:
1. **Deterministic Execution:** The default test suite operates 100% offline using mocked external responses. No live external network dependencies are required to run automated unit and integration tests.
2. **Comprehensive Boundary Coverage:** All weather risk thresholds (wind, rain, snow) and load-dependent trucking rules are tested at exact boundary transitions.
3. **Multi-Layer Validation:** Tests cover serializers, view handlers, middleware, service orchestrators, and caching layers.
4. **Optional Live Smoke Testing:** A dedicated live integration test suite validates end-to-end communication with real OpenStreetMap, OSRM, and Open-Meteo public endpoints on demand.

---

## 2. Test File Breakdown

| Test File | Test Count | Description |
| :--- | :--- | :--- |
| `backend/tests/test_risk_engine.py` | 10 | Exact boundary values for wind (24.9 vs 25), rain (0.10, 0.25, 0.50, 1.00), snow (0.50, 1.00, 2.00, 3.00), load-dependent wind rules (>30k lbs, >40k lbs), mileage summarization, multi-factor ranking, and recommendation rationale. |
| `backend/tests/test_geocoding.py` | 6 | Nominatim primary lookup, Open-Meteo fallback on HTTP 403 / timeout, in-memory caching, 404 location not found, and empty query validation. |
| `backend/tests/test_routing_provider.py` | 6 | OSRM response parsing, route deduplication (filtering identical routes within 1.5% distance/duration), timeout handling, rate limiting (429), and commercial truck adapter fallback. |
| `backend/tests/test_weather_service.py` | 5 | Timezone-aware ETA interpolation, multi-coordinate batching (single HTTP call for up to 30 coords), rounded-coordinate TTL caching, unit conversions, and forecast horizon boundary errors. |
| `backend/tests/test_checkpoints.py` | 4 | Great-circle Haversine math, checkpoint resampling at 10, 25, and 50 miles, milestone preservation (mile 0 and total miles), and offset seconds calculation. |
| `backend/tests/test_api_endpoints.py` | 11 | `/api/health/`, `/api/geocode/`, `/api/plan/`, CORS preflight OPTIONS headers, allowed origins (localhost, 127.0.0.1, Vercel preview regexes), DRF serializer field validation (negative load, excessive load >100k, past departure, unsupported spacing). |
| `backend/tests/test_risk.py` | 2 | Legacy test suite compatibility. |
| `backend/tests/test_live_smoke.py` | 1 | Live external provider smoke test (skipped by default; enabled via `RUN_LIVE_TESTS=1`). |
| **Total Test Cases** | **45** | **44 Unit/Mocked + 1 Live Integration** |

---

## 3. Running Tests

### 3.1 Run All Automated Offline Tests
```bash
.venv/bin/pytest backend/tests
```
Expected output:
```
======================== 44 passed, 1 skipped in ~1.9s =========================
```

### 3.2 Run with Verbose Details
```bash
.venv/bin/pytest backend/tests -v
```

### 3.3 Run Specific Test Suites
```bash
# Risk engine only
.venv/bin/pytest backend/tests/test_risk_engine.py

# API endpoints and CORS only
.venv/bin/pytest backend/tests/test_api_endpoints.py
```

### 3.4 Run Live External Provider Smoke Test
```bash
RUN_LIVE_TESTS=1 .venv/bin/pytest backend/tests/test_live_smoke.py -v
```

---

## 4. Frontend Type Checking & Build Verification
```bash
cd frontend
npm run build
```
Ensures zero TypeScript compilation errors and successful production bundling with Vite.
