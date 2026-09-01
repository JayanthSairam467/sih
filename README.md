# 🌊 SAGAR RAKSHAK (सागर रक्षक — "Ocean Guardian")

**AI-fused Satellite–AIS Maritime Pollution Attribution & Response Platform**

> **SIH26143** · Smart India Hackathon · Theme: Space Technology · Sponsor: **NTRO**

---

## What It Does

Detects oil spills at sea from SAR satellite imagery, correlates them with AIS vessel-tracking data, and identifies the most likely responsible vessel — with full explainable attribution scoring.

### Three differentiators over a "me too" submission:

1. **Explainable attribution, not a black box.** Every "this vessel did it" alert shows its 5-component score breakdown — spatial proximity, temporal fit, AIS gap, course/speed anomaly, and vessel type prior.

2. **Dark-vessel detection as a first-class feature.** Explicitly flags AIS gaps (a vessel that went silent near the spill's estimated origin) as the highest-suspicion case. This is the feature that makes this a *national-security* tool, not just an environmental dashboard.

3. **Forward + backward drift prediction.** Same physics engine runs both directions — backward to find the culprit's origin point, forward to predict spread for response teams deploying containment booms.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION LAYER                          │
│  Sentinel-1 SAR tiles  │  AIS position streams  │  Wind/current data  │
└───────────────┬───────────────────┬──────────────────────┬───────────┘
                │                   │                      │
                ▼                   ▼                      ▼
     ┌─────────────────┐  ┌──────────────────┐   ┌───────────────────┐
     │ SPILL DETECTION  │  │  AIS TRACK STORE  │   │  DRIFT ENGINE      │
     │ U-Net / NumPy    │  │  (gap detection,  │   │  (wind + current   │
     │ 5-class segment: │  │  MMSI/IMO lookup) │   │  vector advection, │
     │ sea/oil/look-    │  │                   │   │  backward + forward│
     │ alike/ship/land  │  │                   │   │                    │
     └────────┬─────────┘  └─────────┬─────────┘   └──────────┬─────────┘
              │                      │                        │
              └──────────┬───────────┴────────────┬───────────┘
                         ▼                        ▼
              ┌────────────────────────────────────────────┐
              │      ATTRIBUTION / CORRELATION ENGINE        │
              │  5-component composite scoring formula       │
              └───────────────────┬────────────────────────┘
                                  ▼
              ┌────────────────────────────────────────────┐
              │         COMMAND-CENTER DASHBOARD (Web)        │
              │  MapLibre map · spill overlay · vessel tracks  │
              │  suspect ranking with evidence breakdown      │
              └────────────────────────────────────────────┘
```

### Attribution Scoring Formula

```
composite_score(vessel) =
    0.30 × spatial_proximity_score     # Closer to drift-origin = higher
  + 0.25 × temporal_fit_score          # Present during spill window
  + 0.20 × ais_gap_bonus              # AIS-dark during window = large bonus
  + 0.15 × course_speed_anomaly_score  # Sudden slowdown/course change
  + 0.10 × vessel_type_prior           # Tankers/cargo > fishing > passenger
```

Every alert shows these 5 components as a visible breakdown — the "explainable AI" story.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js + TypeScript + Tailwind CSS + MapLibre GL JS |
| **Backend** | Python FastAPI |
| **ML** | PyTorch (U-Net) with numpy/scipy fallback |
| **Geospatial** | MapLibre GL (vector tiles), custom GeoJSON overlays |
| **Deployment** | Docker Compose (one command) |

---

## Quick Start

### Option 1: Docker Compose (recommended)

```bash
docker compose up --build
```

Frontend: http://localhost:3000
Backend API: http://localhost:8000/docs

### Option 2: Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Demo Mode

The app ships with **two pre-built real-world incidents** that run entirely on local fixture data — zero external API calls needed:

### 1. Sabiti Tanker Incident — Jeddah (2019)
- **What happened:** Iranian oil tanker damaged near Jeddah, SAR imagery captured oil trail
- **Demo shows:** Dark-vessel detection (AIS gap flagged), 4 candidate vessels ranked, drift-backward to estimated origin
- **Why it matters:** Classic illegal-discharge pattern with AIS evasion

### 2. X-Press Pearl Disaster — Colombo (2021)
- **What happened:** Container ship fire and sinking, major Indian Ocean pollution event
- **Demo shows:** Attribution in a multi-vessel scenario, forward drift prediction for response
- **Why it matters:** One of the worst maritime disasters in the Indian Ocean region

Select either incident from the dropdown — the entire pipeline (detection → AIS correlation → attribution → drift) runs in <1 second on local data.

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/demo/incidents` | GET | List available demo incidents |
| `/api/demo/incidents/{id}` | GET | Full incident data (detection + AIS + attribution + drift) |
| `/api/detection/detect` | POST | Run spill detection on SAR tile |
| `/api/detection/detect-synthetic` | POST | Generate and detect on synthetic SAR |
| `/api/detection/samples` | GET | Generate batch of synthetic SAR samples |
| `/api/ais/ingest` | POST | Ingest AIS position records |
| `/api/ais/tracks` | GET | Get all vessel tracks |
| `/api/ais/gaps` | GET | Get all detected AIS gaps |
| `/api/drift/backward` | POST | Trace backward to estimate origin |
| `/api/drift/forward` | POST | Predict forward spill trajectory |
| `/api/attribution/score` | POST | Score vessels against a spill |
| `/api/attribution/weights` | GET | Get current scoring weights |

---

## Data Sources

| Source | Purpose | Access |
|--------|---------|--------|
| **Sentinel-1 SAR** | Primary spill detection imagery | Free via Copernicus/ASF Vertex |
| **Krestenitis et al. (2019)** | Training dataset (5-class SAR segmentation) | Zenodo open release |
| **AISstream.io** | Real-time AIS WebSocket feed | Free tier available |
| **MarineCadastre.gov** | Historical AIS CSV records | Free download |
| **Open-Meteo Marine API** | Wind/current data for drift model | Free, no API key |
| **NOAA ERDDAP** | Ocean current data | Free, no API key |

---

## ⚠️ What's Simplified (Honesty Section)

This is a hackathon prototype. Be upfront with judges about what's production-grade and what's not:

| Component | What We Built | What Production Would Need |
|-----------|--------------|---------------------------|
| **SAR Detection** | NumPy thresholding + skeleton U-Net architecture | Pretrained U-Net on Krestenitis dataset (~85-90% mIoU) |
| **Drift Model** | Simplified Lagrangian advection: `displacement = (current + 0.03 × wind) × dt` | Full HYCOM/OpenDrift with real-time ocean model data |
| **AIS Data** | Pre-reconstructed synthetic tracks for 2 incidents | Live AISstream.io WebSocket feed with real-time ingestion |
| **Attribution** | 5-component scoring with configurable weights | ML-trained weighting, historical false-positive analysis |
| **SAR Tile** | 256×256 synthetic tiles | Real Sentinel-1 GRD/SLC tiles (5m resolution, 256km swath) |

The **drift model** is deliberately scoped: state clearly that it's a simplified physics approximation (well-established in literature), not a full ocean-model simulation. Judges respect honest scoping far more than overclaimed accuracy.

The **scoring formula weights** (0.30/0.25/0.20/0.15/0.10) are starting points — in production, these would be calibrated against historical ground-truth data.

---

## For the Actual SIH Round

When you advance to the real hackathon, upgrade these components:

1. **Download the Krestenitis dataset** from Zenodo and train the U-Net checkpoint
2. **Connect to AISstream.io** WebSocket for live AIS ingestion
3. **Add Open-Meteo Marine API** calls for real wind/current data in the drift model
4. **Build PDF evidence report** export (the `reportlab` dependency is already included)
5. **Integrate real Sentinel-1 tiles** from Copernicus Data Space Ecosystem

---

## Built For

**SIH26143** — "Leveraging satellite imagery to determine oil spills at sea along with AIS data correlations to identify the vessel responsible for the spill."

Sponsored by **NTRO** (National Technical Research Organisation). Designed as a feeder system into India's maritime domain awareness ecosystem — specifically the **Indian Navy/Coast Guard's IFC-IOR and IMAC** at Gurugram.

---

## License

Hackathon prototype — not for production use.
