# CrowdEye AI - Enterprise Crowd Safety & Security Operations Platform

> **Intelligent Multi-Camera Telemetry, Explainable AI Risk Prediction, Distributed AI Workers, and Security Control Room Operations for Large Public Events**

CrowdEye AI is a production-grade, distributed crowd safety platform engineered for stadiums, music festivals, transit terminals, and large public gatherings. It ingests multi-camera CCTV/RTSP feeds, executes real-time person detection (YOLOv8) and deep multi-object tracking (DeepSORT), computes pedestrian density and velocity vectors using wall-clock timestamps, predicts stampede and surge hazards before escalation, and provides an operator control room dashboard for immediate incident response.

---

## 🏗️ Production System Architecture

```
[ Frontend: Web Dashboard ] (Vercel)
         │  HTTPS / WSS
         ▼
[ FastAPI Backend Gateway ] (Railway / Render / AWS EC2)
    ├── Supabase Auth JWT Validation & RBAC (ADMIN vs OPERATOR)
    ├── SlowAPI Rate Limiting (100 req/min public, 300 req/min user)
    ├── Camera & Alert Management Endpoints
    ├── Realtime WebSocket Hub (Pub/Sub Event Bus)
    └── Security Hardened CORS (Whitelisted Origin Only)
         │                              │
         │ PostgreSQL Over SSL          │ Internal Queue / Service Auth
         ▼                              ▼
[ Supabase PostgreSQL ]           [ Decoupled AI Worker ] (GPU/CPU Server)
    ├── profiles & RBAC               ├── UnifiedInferenceEngine (YOLOv8n + DeepSORT)
    ├── cameras & zone configs        ├── Wall-Clock Kinematics (Speed & Growth)
    ├── alerts (Duplicate Guarded)    ├── Adaptive Frame Sampler (Load-Aware)
    └── Production B-Tree Indexes     └── Multi-Camera Ingestion Queue
```

---

## 🚀 Key Modules & Phase 7 Capabilities

| Module | Core Responsibility | Technologies |
| :--- | :--- | :--- |
| **Decoupled AI Worker** | Ingests video streams, executes YOLOv8 + DeepSORT tracking, computes wall-clock velocity and crowd growth rate. Isolated from API server. | Python 3.11, Ultralytics YOLOv8n, DeepSORT (MobileNet), OpenCV |
| **FastAPI Backend Gateway** | High-performance REST & WebSocket gateway managing authentication, RBAC, camera registry, alerts, and metrics. | FastAPI, SlowAPI, Pydantic v2, PyJWT, WebSockets |
| **Supabase PostgreSQL** | Cloud-native relational database with RLS policies, duplicate-alert partial unique indexes, and production query indexes. | PostgreSQL 15, PostgREST, Row Level Security |
| **Security Operations UI** | Mission-control responsive interface with live camera grid, real-time alert triage, interactive density heatmaps, and a Hackathon Demo Controller. | HTML5, CSS3, ES6 JavaScript, Chart.js, Glassmorphism UI |

---

## ⏱️ Wall-Clock AI Time Calculations (Task 1)

Never assuming fixed video FPS, CrowdEye AI strictly measures spatial kinematics against physical wall-clock timestamps (`time.time()`):

1. **Every Detection Point Stores**:
   ```json
   {
     "timestamp": 1727078400.125,
     "person_position": [342, 510],
     "person_id": 42
   }
   ```
2. **Speed Calculation**:
   $$\text{Speed} = \frac{\text{Euclidean Distance (pixels)}}{\Delta t (\text{seconds})} \quad [px/s]$$
3. **Crowd Growth Rate**:
   $$\text{Growth Rate} = \frac{\text{Current Count} - \text{Previous Count}}{\text{Previous Count} \times \Delta t_{\text{window}}} \quad [\%/s]$$
   *(e.g., 200 people $\to$ 240 people over 10 seconds yields $+2.0\%/s$ or $+20\%$ over the 10-second window).*

---

## ⚡ AI Performance Optimizations (Task 2)

- **Single Model Load**: YOLOv8n weights loaded exactly once during application / worker startup (`load_model_once()`) and reused via thread-safe singleton instances. Zero per-request reloading overhead.
- **Adaptive Frame Sampling**: Dynamically throttles inference workload based on running latency:
  - **Normal Load** ($\le 80\text{ ms}$): Ingests every 2nd frame.
  - **High Load** ($> 80\text{ ms}$): Dynamically samples every 5th frame to prevent stream latency accumulation.

---

## 🔒 Security Hardening, JWT Auth & RBAC (Tasks 5, 6, 7, 8)

1. **Supabase Auth JWT Dependency** (`app.auth.auth`):
   - Validates `Authorization: Bearer <token>` on all sensitive endpoints.
   - Decodes Supabase claims and verifies role assignment in `profiles` table.
2. **Role-Based Access Control (RBAC)**:
   - **`ADMIN`**: Full permissions — Camera registration/editing (`POST /cameras`, `PUT /cameras/{id}`), Alert lifecycle management, System configuration.
   - **`OPERATOR`**: Security monitoring — Dashboard overview, live camera streams, heatmap viewer, and Alert resolution (`PUT /alerts/{id}/resolve`). Modifying cameras returns `HTTP 403 Forbidden`.
3. **CORS Hardening**: Wildcard origin `*` strictly blocked in production. Enforces exact `FRONTEND_URL` whitelist.
4. **SlowAPI Rate Limiting**:
   - **Public Endpoints** (`/health`, `/api/v1/health`): `100 requests/minute per IP`.
   - **Authenticated APIs** (`/cameras`, `/alerts`, `/dashboard`): `300 requests/minute per user`.
   - **Internal AI Pipeline**: Bypasses rate limits using internal service token.

---

## 🩺 System Health Monitoring (Task 9)

Endpoint: `GET /health` or `GET /api/v1/health`

### Response Schema:
```json
{
  "api": "healthy",
  "database": "connected",
  "ai_worker": "running",
  "model_status": "loaded",
  "demo_mode": false
}
```
*(When `DEMO_MODE=true`, `model_status` automatically reports `"simulation"`).*

---

## 🎭 Hackathon Demo Mode & Flow (Tasks 11 & 15)

CrowdEye AI includes a built-in simulation engine for pitch presentations without requiring live stadium camera hardware:

- Enable via environment: `DEMO_MODE=true`
- **Scenario Control API**:
  - `POST /demo/scenario` with payload `{"scenario": "low" | "medium" | "critical"}`
- **Interactive UI Bar**: In `dashboard.html`, operators and judges can click:
  - 🟢 **Normal Flow**: Risk Score 18 (Safe, normal velocity)
  - 🟡 **Elevated Crowd**: Risk Score 58 (Monitoring surge)
  - 🔴 **Critical Surge**: Risk Score 92.5 (Triggers real-time Critical safety alert and alert sound)
  - ✅ **Reset**: Clears alerts and resets baseline

### Hackathon Demo 8-Step Walkthrough:
1. **Operator Login**: Sign in with Operator credentials (`operator@crowdeye.internal`).
2. **Open Dashboard**: Overview shows 4 active cameras, 0 high-risk alerts.
3. **View CCTV Grid**: Live multi-camera feeds with real-time bounding boxes and headcounts.
4. **AI Detects Crowd**: Pedestrian density concentrates in Zone C (Main Stage).
5. **Heatmap Appears**: Visual spatial heatmap illuminates red hotspot.
6. **Risk Increases**: Explainable AI engine raises score to 92.5 due to simultaneous density spike and velocity drop.
7. **Alert Generated**: Red incident banner activates with audio chime and duplicate protection.
8. **Operator Resolves Alert**: Operator clicks "Resolve Incident", logging resolution audit and clearing alert across connected clients via WebSockets.

---

## 📊 Benchmark & Performance Report (Task 12)

Results from the automated benchmark suite (`scratch/test_phase7_performance.py`):

| Benchmark Test | Metric Measured | Target | Verified Performance | Result |
| :--- | :--- | :--- | :--- | :--- |
| **Test 1: Single Camera AI** | FPS & Latency | $> 5.0\text{ FPS}$ | **$15.3\text{ FPS}$** ($65.47\text{ ms}$ avg latency) | **PASS** |
| **Test 2: 5-Camera Simulation** | Concurrent Ingestion Delay | $< 350\text{ ms}$ | **$306.62\text{ ms}$** delay ($15.6\text{ FPS}$ throughput) | **PASS** |
| **Test 3: 100 Dashboard Users** | Concurrent Request Latency | 100% handled | **$384.40\text{ ms}$** avg, **$791.69\text{ ms}$** p95 (100/100 handled) | **PASS** |
| **Test 4: Health & Rate Limits** | SlowAPI Trigger on Burst | HTTP 429 | Triggered exactly at request #100 | **PASS** |

---

## 🐳 Docker Deployment (Task 4)

CrowdEye AI is packaged as containerized microservices ready for cloud execution:

### 1. Build and Run via Docker Compose:
```bash
# Clone the repository
git clone https://github.com/SanskarEdhate/CrowdEye.git
cd CrowdEye

# Create environment configuration
cp .env.example .env

# Launch API Backend + AI Worker
docker-compose up --build -d
```

### 2. Verify Services:
```bash
docker-compose ps
curl http://localhost:8000/health
```

*(Supabase PostgreSQL remains a fully managed cloud service; no local database container required).*

---

## 📋 Database Migrations (Task 10)

Located in `database/migrations/`:
- `001_initial_schema.sql` - Core entities (users, events, cameras, crowd logs)
- `002_tracking_schema.sql` - Spatial person tracking tables
- `003_tracking_jobs.sql` - DeepSORT async job tracker
- `004_density_schema.sql` - Zone density and homography configurations
- `005_risk_schema.sql` - Explainable risk scoring logs
- `006_alerts.sql` - Alerts table with duplicate protection & profiles RBAC
- `007_camera_update.sql` - Camera status and zone JSONB schema
- **`008_production_indexes.sql`** - Production performance indexes on `alerts`, `crowd_risk`, and `crowd_density` for high-throughput querying.

---

## 🛠️ Local Development Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ (for Vercel deployment)
- Git

### 1. Install Backend Dependencies
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows: venv\Scripts\activate, Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
```

### 2. Launch FastAPI API Gateway
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Launch AI Worker Service
```bash
cd ai_worker
python worker.py
```

### 4. Serve Security Dashboard
Serve the `frontend/` directory using any static file server:
```bash
python -m http.server 3000 --directory frontend/pages
```
Visit `http://localhost:3000/dashboard.html` in your browser.

---

## 📖 Deployment Documentation

For detailed cloud deployment steps across Vercel, Render/Railway, AWS EC2, and Supabase, refer to:
👉 **[docs/deployment.md](docs/deployment.md)**

---

## 🛡️ License

MIT License. Designed and engineered for crowd safety at major public venues.
