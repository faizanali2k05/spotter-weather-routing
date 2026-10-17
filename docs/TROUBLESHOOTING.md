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

