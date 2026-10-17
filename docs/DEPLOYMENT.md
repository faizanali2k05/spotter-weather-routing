# Spotter Weather-Aware Truck Routing — Deployment Guide

This document describes production deployment procedures for the backend on **Render** (via Docker) and the frontend on **Vercel**.

---

## 1. Architecture Overview

- **Backend:** Containerized Django REST Framework web service deployed to Render Web Services using Docker.
- **Frontend:** Static React/TypeScript SPA deployed to Vercel Global Edge Network.
- **Data Stores:** SQLite default; stateless routing and weather querying with in-memory caching.

---

## 2. Backend Deployment (Render Docker Service)

The repository includes a ready-to-use Render Blueprint specification (`render.yaml`).

### 2.1 Render Service Settings
- **Service Type:** Web Service
- **Runtime:** Docker
- **Docker Build Context:** `./backend`
- **Dockerfile Path:** `./backend/Dockerfile`
- **Health Check Path:** `/api/health/`
- **Auto-Deploy:** Enabled on push to `main`

### 2.2 Required Environment Variables on Render
Configure these in the Render Dashboard under **Environment**:

| Key | Example Value | Notes |
| :--- | :--- | :--- |
| `DJANGO_SECRET_KEY` | *(Generate 50+ random chars)* | Generate automatically or provide via secret generator. |
| `DEBUG` | `false` | Must always be `false` in production. |
| `ALLOWED_HOSTS` | `.onrender.com,api.yourdomain.com` | Allows Render subdomains. |
| `CORS_ALLOWED_ORIGINS` | `https://spotter-weather-routing.vercel.app` | Your production Vercel frontend domain. |

### 2.3 Docker Build Verification
During Render build, the Dockerfile automatically executes:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
```
Static files are compressed and fingerprinted with WhiteNoise (`CompressedManifestStaticFilesStorage`).

---

## 3. Frontend Deployment (Vercel)

### 3.1 Project Import & Build Settings
1. In the Vercel dashboard, click **Add New Project** and select `spotter-weather-routing`.
2. Configure project settings:
   - **Framework Preset:** `Vite`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
   - **Install Command:** `npm install`

### 3.2 Environment Variables on Vercel
Add the following under **Project Settings > Environment Variables**:

| Key | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://spotter-weather-routing-api.onrender.com` | Base URL of your deployed Render backend. |

---

## 4. Post-Deployment Verification

1. **Verify Backend Health:**
   ```bash
   curl -I https://spotter-weather-routing-api.onrender.com/api/health/
   # Expect HTTP/2 200 OK
   ```

2. **Verify CORS Preflight:**
   ```bash
   curl -I -X OPTIONS https://spotter-weather-routing-api.onrender.com/api/plan/ \
     -H "Origin: https://spotter-weather-routing.vercel.app" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type"
   # Expect access-control-allow-origin: https://spotter-weather-routing.vercel.app
   ```

3. **Verify End-to-End Route Calculation:**
   Open the production Vercel URL in a browser, enter `New York, NY` to `Philadelphia, PA`, and confirm routes, checkpoints, and spatial weather heatmaps render correctly.

