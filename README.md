# Planetes

Explore thousands of real satellites, debris objects, rocket bodies, and near-Earth asteroid approaches around an interactive 3D Earth.

**[Live](https://planetes-livid.vercel.app)** · **[Backend health](https://planetes-backend.onrender.com/api/health)** · **[API metrics](https://planetes-backend.onrender.com/api/metrics)**

---

## What is Planetes?

Planetes is an interactive orbital-data explorer. It turns a large public catalogue of objects around Earth into something that can be searched, filtered, clicked, and understood without reading raw orbital records.

The project combines real satellite and debris data from KeepTrack, near-Earth approach data from NASA, current-position calculation using SGP4, and a small investigation workflow that explains the selected object without pretending to be an operational collision-avoidance system.

## What you can do

- Browse up to 2,000 propagated orbital objects at once.
- Filter active satellites, debris, and rocket bodies.
- Click an object to inspect its name, catalogue ID, altitude, velocity, source, and orbital details.
- View NASA near-Earth asteroid approach events.
- Request a structured investigation report for the selected object.
- Continue using the core application when an external AI provider is unavailable through deterministic fallback reports.

## Verified scale

The following numbers were measured from the deployed backend rather than estimated:

- **36,053** KeepTrack catalogue records ingested.
- **33,521** usable orbital records after validation and classification.
- **2,000** real orbital objects propagated and returned in a single request.
- Verified 2,000-object sample: **802 satellites, 800 debris objects, and 398 rocket bodies**.
- **38** NASA near-Earth approach events in the verified response.
- **0 synthetic orbital objects** in the active data path.
- Approximately **1,019 propagated objects/second** in the measured backend run.
- **0.01 ms** warm catalogue-cache lookup.
- **22 passing backend tests** after the catalogue and rendering-scale work.

These figures can vary as upstream catalogues and NASA feeds change.

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

## Engineering history: what broke and what changed

This project did not arrive in its current form in one clean pass. The useful part of the process was learning which technically attractive ideas made the product worse.

### 1. The first ambitious globe rewrite was a downgrade

An early revision replaced the stable textured Earth with procedural rendering and more custom shader work. It was harder to maintain, visually worse, and introduced repeated build problems.

**Decision:** restore the working textured globe and treat visual stability as a product requirement rather than a temporary compromise.

### 2. One pickable mesh per object did not scale

The first selection system created an additional sphere for every object. That was acceptable for a tiny prototype but wasteful near thousands of objects.

**Decision:** render category batches as `THREE.Points` and use `intersection.index` to map a raycast hit back to the correct object. Filtering now rebuilds the visible point buffers and their index mappings together.

### 3. The original data path stopped at a few dozen objects

The first backend fetched individual satellite IDs. That produced a visually convincing prototype but could not support a meaningful scale claim.

**Decision:** integrate KeepTrack's brief catalogue endpoint, validate 36,053 TLE records, classify the usable records, and cache the catalogue for 24 hours.

### 4. Eager embedding-model startup nearly made deployment impractical

The original investigation path loaded SentenceTransformers, Transformers, and PyTorch at application import time. The measured import peak was roughly 936 MiB and could contact Hugging Face during startup.

**Decision:** remove that model from the active runtime. Import memory dropped to roughly 78.5 MiB, and the running API stayed near 93 MiB after live requests.

### 5. Synthetic data made the screen fuller but the project weaker

Random debris and fallback positions made early versions look busier, but they blurred the difference between real records and invented coordinates.

**Decision:** disable synthetic debris, reject unusable orbital candidates, remove random satellite-position fallback, and label NASA placement as non-ephemeris.

### 6. Local success did not guarantee a clean deployment

Groq worked locally after a manual package installation but Render failed because the dependency was not declared. The first Vercel deployment also exposed monorepo-root and environment-variable mistakes.

**Decision:** validate from fresh requirements, keep deployment commands repository-root aware, expose a real health endpoint, and document the required Render/Vercel variables.

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
npm install
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

---

Built as a portfolio project, but treated as a real engineering exercise: preserve what works, measure before claiming scale, and remove anything that makes the result look more impressive than the underlying data.
