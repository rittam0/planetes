# Planetes

Explore thousands of real satellites, debris objects, rocket bodies, and near-Earth asteroid approaches around an interactive 3D Earth.

**[Live](https://planetes-livid.vercel.app)** · **[Backend health](https://planetes-backend.onrender.com/api/health)** · **[API metrics](https://planetes-backend.onrender.com/api/metrics)**

---

## What is Planetes?

Planetes is an interactive orbital-data explorer. It turns a large public catalogue of objects around Earth into something that can be searched, filtered, clicked, and understood without reading raw orbital records.

FastAPI ingests real KeepTrack catalogue records, validates TLE pairs, propagates current positions with SGP4, and serves a bounded set of objects to a React/TypeScript/Three.js scene. NASA NeoWs supplies near-Earth approach records. An optional external LLM produces structured selected-object investigations, with deterministic fallback when it is unavailable.

## What you can do

- Browse up to 2,000 propagated orbital objects at once.
- Filter active satellites, debris, and rocket bodies.
- Click an object to inspect its name, catalogue ID, altitude, velocity, source, and orbital details.
- View NASA near-Earth asteroid approach events.
- Request a structured investigation report for the selected object.
- Continue using the core application when an external AI provider is unavailable through deterministic fallback reports.

## Scale and evidence

The default product path selects up to **2,000 orbital objects**; unusable TLEs
and failed propagation are excluded. [Catalogue tests](backend/tests/test_orbital_catalogue.py)
verify the configured limit, validation, classification, SGP4 propagation and
24-hour cache behavior with fixtures. The frontend batches category point
buffers for rendering and selection.

Catalogue size and returned composition vary with upstream data and propagation
success. Previous README catalogue counts and throughput/cache timings lacked a
committed run artifact or reproducible measurement procedure, so they are not
used as verified performance claims here. Fixture tests establish behavior;
they do not measure live ingestion scale or browser/GPU throughput.

## How the data should be interpreted

Planetes deliberately separates source data from visual approximation:

- Satellite, debris, and rocket-body records come from the KeepTrack catalogue.
- Their displayed current positions are derived from valid TLE pairs using SGP4.
- NASA object names, sizes, hazard flags, velocities, miss distances, and approach dates come from NeoWs.
- NASA asteroid placement in the 3D scene is representative, not a precise ephemeris.
- Investigation results are explanatory portfolio outputs, not operational collision probabilities or manoeuvre advice.

## Architecture

```text
Vercel
└── React + TypeScript + Three.js
    ├── interactive Earth and atmosphere
    ├── batched point rendering
    ├── point-index raycast selection
    ├── filters and object details
    └── selected-object investigation UI

Render
└── FastAPI
    ├── KeepTrack catalogue ingestion
    ├── 24-hour in-memory catalogue cache
    ├── TLE validation and object classification
    ├── SGP4 current-position propagation
    ├── NASA NeoWs approach ingestion
    ├── conditional investigation workflow
    ├── Groq structured reports with deterministic fallback
    └── health and metrics endpoints
```

## Design decisions

- Keep a textured globe and batch orbital objects as `THREE.Points`. Raycast
  `intersection.index` maps into the visible object array; filtering updates
  the buffers and mappings together.
- Fetch a catalogue instead of individual satellite IDs, validate candidates,
  and cache records in memory for 24 hours.
- Reject unusable orbital candidates rather than fill the scene with synthetic
  debris or random fallback satellite positions.
- Keep external model calls optional. The investigation layer explains selected
  objects and provides deterministic fallback reports without loading a local
  embedding model at application startup.

## Run locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Create `backend/.env` or export these variables:

```text
KEEPTRACK_API_KEY=...
NASA_API_KEY=...
GROQ_API_KEY=...        # optional; deterministic fallback works without it
ALLOWED_ORIGINS=http://localhost:3000
```

Useful endpoints:

```text
GET  /api/health
GET  /api/objects?limit=2000
GET  /api/metrics
POST /api/investigate
```

### Frontend

```bash
cd frontend
npm ci
VITE_API_URL=http://localhost:8000/api npm run dev
```

Then open the Vite URL shown in the terminal.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests -v
```

Frontend checks:

```bash
cd frontend
npx tsc --noEmit
npm run build
```

CI runs backend tests, TypeScript checks, the frontend production build and both
Docker image builds on pushes and pull requests. Image builds use `push: false`
and require no Docker Hub credentials.

## Deployment

### Render backend

- Build command: `pip install -r backend/requirements.txt`
- Start command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health check: `/api/health`
- Required variables: `KEEPTRACK_API_KEY`, `NASA_API_KEY`, `ALLOWED_ORIGINS`
- Optional variable: `GROQ_API_KEY`

### Vercel frontend

- Repository-root deployment using the committed `vercel.json`
- Required production variable:

```text
VITE_API_URL=https://planetes-backend.onrender.com/api
```

The Vercel production origin must also be present in Render's `ALLOWED_ORIGINS`.

## Known limitations

- Planetes is not an operational conjunction-assessment or collision-avoidance system.
- NASA asteroid positions in the scene are representative rather than exact heliocentric/geocentric ephemerides.
- The catalogue is cached in process memory; multiple backend instances would need a shared cache.
- The public backend may cold-start on the hosting free tier.
- Browser performance depends on device and GPU; the verified production target is 2,000 rendered orbital objects.

## Stack

**Frontend:** React, TypeScript, Three.js, Vite, Zustand  
**Backend:** FastAPI, Python, HTTPX, SGP4  
**Data:** KeepTrack API, NASA NeoWs  
**AI:** LangGraph state routing, Groq structured output, deterministic fallback  
**Delivery:** Render, Vercel, PyTest
