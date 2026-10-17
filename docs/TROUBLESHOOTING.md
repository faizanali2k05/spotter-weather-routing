# Spotter Weather-Aware Truck Routing — Troubleshooting Guide

This guide details common issues, error codes, root causes, and verified resolutions.

---

## 1. Browser "Failed to fetch" or "CORS error"

### Symptom
Browser developer console displays:
```
Access to fetch at 'http://127.0.0.1:8000/api/plan/' from origin 'http://127.0.0.1:5173'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

### Root Cause
1. Frontend opened using `127.0.0.1:5173` while Django backend only whitelisted `http://localhost:5173`.
2. Missing or incorrectly ordered `CorsMiddleware` in `settings.py`.
3. Vercel preview domain not included in `CORS_ALLOWED_ORIGIN_REGEXES`.

### Resolution
1. Verify `backend/config/settings.py` includes `CorsMiddleware` as the first middleware entry:
   ```python
   MIDDLEWARE = [
       'corsheaders.middleware.CorsMiddleware',
       'django.middleware.security.SecurityMiddleware',
       ...
   ]
   ```
2. Ensure `CORS_ALLOWED_ORIGINS` includes both `http://localhost:5173` and `http://127.0.0.1:5173`.
3. For Vercel preview branches, verify `CORS_ALLOWED_ORIGIN_REGEXES = [r"^https:\/\/.*\.vercel\.app$"]` is configured.
4. Test CORS preflight using curl:
   ```bash
   curl -I -X OPTIONS http://127.0.0.1:8000/api/plan/ \
     -H "Origin: http://127.0.0.1:5173" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type"
   ```

---

## 2. "Routing or weather provider unavailable. Please try again."

### Symptom
Application displays generic 502 error banner when submitting a trip.

### Root Cause
1. **User-Agent Rejection:** Open-Meteo's cloud infrastructure issues HTTP 503 if requests use default `python-requests` User-Agent or lack `Mozilla/5.0` compatibility prefix.
2. **Nominatim 403 Access Denied:** OpenStreetMap Nominatim blocks generic bot scrapers.
3. **Sequential Request Exhaustion:** Previous implementation fired up to 60 individual single-coordinate HTTP calls per plan, exceeding rate limits.

### Resolution
1. Verify all outbound requests in `geocoding.py`, `routing_provider.py`, and `weather_service.py` send a custom compliant User-Agent:
   `Mozilla/5.0 (compatible; SpotterWeatherRouting/2.0; +https://github.com/faizanali2k05/spotter-weather-routing)`
2. Ensure automatic geocoding fallback to Open-Meteo Geocoding API is active if Nominatim returns HTTP 403 or 429.
3. Multi-coordinate batching (`fetch_batch_forecasts`) groups coordinates into single queries of up to 30 points.
4. In-memory TTL caching (15 minutes) prevents repetitive external API calls.

---

## 3. Docker Build Error: `collectstatic` Failure

### Symptom
Render Docker build fails during `RUN python manage.py collectstatic --noinput`.

### Root Cause
- Missing `STATIC_ROOT` path in `settings.py` or invalid syntax in Django configuration.
- Missing default fallback for `DJANGO_SECRET_KEY` during static build stage.

### Resolution
1. Ensure `settings.py` defines:
   ```python
   STATIC_URL = '/static/'
   STATIC_ROOT = BASE_DIR / 'staticfiles'
   STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
   ```
2. Verify `DJANGO_SECRET_KEY` defaults safely if omitted at build time:
   `SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'default-build-key')`
3. Test locally:
   ```bash
   python manage.py collectstatic --noinput
   ```

---

## 4. TypeScript Build Error: `Property 'env' does not exist on type 'ImportMeta'`

### Symptom
`npm run build` fails with:
```
error TS2339: Property 'env' does not exist on type 'ImportMeta'.
```

### Root Cause
Vite client environment types not referenced in `tsconfig.json`.

### Resolution
1. Add `frontend/src/vite-env.d.ts`:
   ```typescript
   /// <reference types="vite/client" />
   ```
2. Update `frontend/tsconfig.json` compilerOptions:
   ```json
   "types": ["vite/client"]
   ```

---

## 5. MapLibre GL Map Not Rendering / Blank Screen

### Symptom
Map container shows dark background without road networks or tiles.

### Root Cause
1. Invalid or blocked basemap style URL.
2. Container rendered before parent DOM element acquires non-zero dimensions.

### Resolution
1. Basemap style is configured to CartoCDN dark matter:
   `https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json`
2. `MapView` wraps rendering in `map.once('load', ...)` or checks `map.isStyleLoaded()`.
3. Check browser network tab for blocked font or tile requests.

---

## 6. Render Production Open-Meteo `PROVIDER_RATE_LIMIT` (HTTP 429)

### Symptom
On Render production, calculating routes returns `HTTP 429` with error code `PROVIDER_RATE_LIMIT`:
```json
{
  "error": "Open-Meteo weather API rate limit exceeded.",
  "code": "PROVIDER_RATE_LIMIT",
  "details": {}
}
```
However, the exact same route works reliably when run locally on developer machines.

### Root Cause
1. **Render Shared Outbound IP Pooling:** Render free and standard container instances share egress IP addresses across many independent tenant applications. Open-Meteo's free tier tracks rate limits strictly by IP address (600 requests/minute, 5,000 requests/hour, 10,000 requests/day). If other container workloads on that Render host or IP block query Open-Meteo, the shared IP's rate limit budget can be exhausted even with minimal traffic from this app.
2. **Sequential Batch Requests:** Previous implementations issued separate batch requests for Route 1, Route 2, Route 3, and then another for the corridor heatmap, creating rapid bursts of 4+ requests per plan calculation.
3. **Non-Resilient Heatmap Generation:** If the optional corridor heatmap hit an HTTP 429 or 503, it caused the entire planning request to fail, discarding already-computed route weather analysis.

### Code-Level Mitigations Implemented
1. **Unified Coordinate Pre-Batching:** All route checkpoints across all alternatives and the corridor grid are consolidated and deduplicated into a single batch query (`BATCH_CHUNK_SIZE=50`), reducing external network requests by ~75%.
2. **Shared 30-Minute In-Memory Cache:** All coordinates use normalized precision (`round(coord, 2)`) with a 30-minute TTL, eliminating duplicate requests for overlapping corridors or repeat queries.
3. **HTTP 429 Backoff & Retry:** When Open-Meteo responds with HTTP 429, the service inspects `Retry-After` headers and retries with exponential backoff rather than failing immediately.
4. **Graceful Heatmap Degradation:** If external rate limits prevent generating the corridor heatmap overlay, the route analysis still succeeds completely with all route alternatives, checkpoints, risk evaluations, and safety recommendations, appending an advisory notice to the response.
5. **Commercial API Key Support:** Setting `OPEN_METEO_API_KEY` in environment variables automatically routes requests to `customer-api.open-meteo.com` with `apikey` authentication.

### Hosting / Infrastructure Solutions
- **Commercial Open-Meteo API Key:** Add `OPEN_METEO_API_KEY=<your_key>` in Render environment variables. This routes traffic to Open-Meteo's dedicated commercial infrastructure, lifting IP-based shared limits.
- **Dedicated Static Outbound IP:** Configure Render with a static outbound IP or deploy an outbound egress proxy (e.g. Squid/HAProxy on a dedicated VPS) so requests do not share noisy-neighbor Render IP pools.

