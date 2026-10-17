# Spotter Weather-Aware Truck Routing

Full-stack assessment project built with React/TypeScript, MapLibre and Django REST Framework. Compares up to three genuine OSRM driving alternatives, samples route checkpoints, retrieves time-aligned Open-Meteo forecasts and ranks routes by the published wind/rain/snow/load rules.

## Important limitations

- **Not a truck navigation system.** Public OSRM demo returns ordinary driving directions and does not enforce vehicle height, weight, or hazmat restrictions.
- OSRM may return **fewer than three** genuinely distinct routes. The application does not fabricate the missing alternatives.
- Forecast API lookups are potentially slow on long routes; no persistent cache is implemented.
- The 0–48 hour slider is a **checkpoint arrival exposure viewer**, not a full spatial weather heatmap. A full corridor heatmap remains to be implemented.
- Checkpoint ETAs are approximated by distance proportion; routing segment speeds are not included.
- Weather is advisory, not a guarantee of safe travel. Delay trips involving No Travel weather. No Travel paths are excluded from recommendation whenever possible.

## API and setup

Python 3.12+ and Node 20+ recommended.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py runserver
```

Separate terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Set `VITE_API_BASE_URL` to the Django origin. For deployment, set `CORS_ALLOWED_ORIGINS` to the exact Vercel frontend URL. No paid API key is required for the current public endpoint demonstration. OpenStreetMap Nominatim and OSRM demo services have fair-use restrictions; this architecture needs a commercial routing/geocoding provider before production use.

`POST /api/plan/` JSON:

```json
{"origin":"New York, NY","destination":"Philadelphia, PA","departure":"2026-10-18T12:00:00Z","load_lbs":35000,"spacing_miles":25}
```

`GET /api/health/` and `GET /api/geocode/?q=New%20York`.

## Risk and recommendation

Wind: Low <25 mph; Moderate 25–34; High 35–44; Severe 45–54; No Travel ≥55. Rain (in/hr): Low <0.10; Moderate 0.10–<0.25; High 0.25–<0.50; Severe 0.50–1.00; No Travel >1.00. Snow (in/hr): Low <0.5; Moderate 0.5–<1.0; High 1.0–<2.0; Severe 2.0–3.0; No Travel >3.0. The highest measured condition severity wins. Wind 45–54 with load >30,000 lb => No Travel; wind 35–44 with load >40,000 lb => Severe.

Routes are sorted first by availability of a No Travel-free path, then by severe mileage, high mileage, distance-weighted average risk, and drive time.

## Deployment

- **Render**: deploy repository as Docker service; Dockerfile `backend/Dockerfile`, context `backend`; health check `/api/health/`. Set `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, and `CORS_ALLOWED_ORIGINS`.
- **Vercel**: import the same repository with Root Directory `frontend`, Framework Preset `Vite`, Build Command `npm run build`, Output Directory `dist`. Set `VITE_API_BASE_URL=https://<your-render-service>.onrender.com` and redeploy.

## Tests

```bash
cd backend && pytest -q
cd frontend && npm run build
```

## 5–10 minute Loom demo

1. Explain architecture and provider limitations.
2. Create a trip with 25-mile checkpoints.
3. Compare actual route alternatives and risk-color-coded mileage.
4. Click checkpoint markers to inspect arrival-time forecasts.
5. Show 0–48 hour timeline and known heatmap limitation.
6. Demonstrate load-dependent risk rules and no-travel behavior.
7. Show tests, repository structure and hosted app.

This project is intended for a coding assessment, not operational dispatch decisions.
