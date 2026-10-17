# Spotter Weather-Aware Truck Routing — Local Setup Guide

Follow this guide to configure and run the full-stack development environment on Linux, macOS, or Windows (WSL2).

---

## Prerequisites

- **Python:** 3.12 or newer
- **Node.js:** 20.x or newer (LTS recommended)
- **Git**

---

## 1. Clone the Repository

```bash
git clone https://github.com/faizanali2k05/spotter-weather-routing.git
cd spotter-weather-routing
```

---

## 2. Backend Setup (Django & DRF)

### 2.1 Create & Activate Virtual Environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
# On Windows PowerShell: .venv\Scripts\Activate.ps1
```

### 2.2 Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2.3 Configure Environment Variables

```bash
cp .env.example .env
```

Default settings in `.env.example` are preconfigured for local development (`DEBUG=true`, `ALLOWED_HOSTS=localhost,127.0.0.1`, `CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`).

### 2.4 Apply Migrations & Collect Static Files

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### 2.5 Start Backend Server

```bash
python manage.py runserver 127.0.0.1:8000
```

Verify backend health by visiting:
[http://127.0.0.1:8000/api/health/](http://127.0.0.1:8000/api/health/)

---

## 3. Frontend Setup (React & Vite)

In a **separate terminal window**:

### 3.1 Install Dependencies

```bash
cd frontend
npm install
```

### 3.2 Configure Environment Variables

```bash
cp .env.example .env
```

Ensure `VITE_API_BASE_URL` points to your local backend:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### 3.3 Start Frontend Development Server

```bash
npm run dev
```

Open your browser to:
[http://localhost:5173](http://localhost:5173)

---

## 4. Running Automated Tests

### 4.1 Backend Test Suite (Fast Unit & Mocked Integration)

From the project root:
```bash
.venv/bin/pytest backend/tests
```

### 4.2 Frontend Build Check

```bash
cd frontend
npm run build
```

### 4.3 Optional Live Integration Smoke Test

To verify end-to-end communication with real OpenStreetMap, OSRM, and Open-Meteo servers:
```bash
RUN_LIVE_TESTS=1 .venv/bin/pytest backend/tests/test_live_smoke.py
```
