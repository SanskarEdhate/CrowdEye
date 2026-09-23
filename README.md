<div align="center">

# 👁️ CrowdEye AI
### Real-Time Crowd Safety Telemetry, Explainable Risk Analytics & Security Operations Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)](https://ultralytics.com)
[![DeepSORT](https://img.shields.io/badge/DeepSORT-RealTime_Tracking-FF6F00?style=for-the-badge)](https://github.com/nwojke/deep_sort)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL_15-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <b>Transforming passive video surveillance into an active, proactive early-warning safety grid for major public events, stadiums, festivals, and transit terminals.</b>
</p>

[System Architecture](#-system-architecture) •
[Key Capabilities](#-key-capabilities) •
[Mathematical Foundations](#-mathematical-foundations) •
[Quickstart](#-quickstart-guide) •
[Docker Deployment](#-docker-deployment) •
[Hackathon Demo Flow](#-hackathon-demo-script--flow) •
[API Reference](#-api-specification)

---

</div>

## 📌 Executive Summary

Modern crowd disasters—such as crowd collapses, stampedes, and turbulent surges—are rarely spontaneous. They are preceded by identifiable physical anomalies: **rapid localized density growth, sudden velocity drops, and high directional movement chaos**.

**CrowdEye AI** is an enterprise-grade, distributed computer vision and safety telemetry platform. By analyzing multi-camera CCTV/RTSP feeds through a decoupled microservices architecture, CrowdEye AI delivers:

1. **Sub-second pedestrian detection and multi-object tracking** through YOLOv8 and DeepSORT.
2. **Physics-accurate spatial velocity and temporal growth rates** computed using strict **wall-clock timestamps**.
3. **Perspective homography correction** to map pixel clusters to real-world metric density ($ppl/m^2$).
4. **An explainable 4-factor risk scoring engine** (0–100) that alerts operators *before* hazardous thresholds are crossed.
5. **A security control room dashboard** with real-time camera grid telemetry, duplicate-protected incident alarms, and one-click incident resolution.

---

## 🏗️ System Architecture

CrowdEye AI utilizes a decoupled microservice topology separating compute-intensive deep learning inference from high-throughput API routing and database persistence.

```
                                  +------------------------------------+
                                  |     Vercel Static Hosting          |
                                  |     Frontend Web Operations UI     |
                                  |  (Dashboard, Cameras, Alerts, Demo)|
                                  +-----------------+------------------+
                                                    |
                                         HTTPS / WSS| (REST + WebSockets)
                                                    v
+---------------------------------------------------------------------------------------------------+
|                                     FastAPI API Gateway                                           |
|                                (Railway / Render / AWS EC2)                                       |
|                                                                                                   |
|  * Supabase Auth JWT Validation                     * SlowAPI Rate Limiting (100/min, 300/min)     |
|  * Role-Based Access Control (ADMIN / OPERATOR)     * Pydantic v2 Strict Request Validation       |
|  * Camera CRUD & Zone Homography Registry           * Realtime WebSocket Hub (Pub/Sub Event Bus)  |
|  * Incident Lifecycle & Duplicate Guard             * CORS Hardened (Origin Whitelist Only)       |
+--------------------------------+----------------------------------+-------------------------------+
                                 |                                  |
               PostgreSQL / RLS  |                                  | Internal Service Token / HTTP
               (Managed Cloud)   |                                  |
                                 v                                  v
+--------------------------------------------------+  +---------------------------------------------+
|               Supabase PostgreSQL                |  |            Decoupled AI Worker              |
|                                                  |  |          (GPU / CPU Container)          |
|  * Table: profiles (RBAC Roles)                  |  |                                             |
|  * Table: cameras (Status, Zone Configs)         |  |  * UnifiedInferenceEngine Singleton         |
|  * Table: alerts (Unique Active Index Constraint)|  |  * YOLOv8n Person Detector (Single Startup) |
|  * Table: crowd_risk & crowd_density             |  |  * DeepSORT Multi-Object Tracker            |
|  * B-Tree Production Indexes (008 Migration)     |  |  * Wall-Clock Velocity & Growth Kinematics  |
|  * Row Level Security (RLS) Policies             |  |  * Load-Aware Adaptive Frame Sampler        |
+--------------------------------------------------+  +---------------------------------------------+
```

---

## ⚡ Key Capabilities

### 1. Decoupled AI Worker (`ai_worker/`)
- Completely decoupled from the client-facing API server to prevent inference workloads from blocking dashboard latency.
- Features `UnifiedInferenceEngine` running thread-safe inference loops with bounded multi-camera ingestion queues.
- Loads model weights once on startup (`load_model_once()`)—zero per-request reloading overhead.
- **Adaptive Frame Sampling**: Dynamically processes every 2nd frame under normal load ($\le 80\text{ ms}$) or throttles to every 5th frame under heavy load ($> 80\text{ ms}$) to prevent video lag.

### 2. Wall-Clock Spatial Kinematics
- Calculates kinematics using physical wall-clock timestamps (`time.time()`), completely independent of video frame rate variations or dropped frames.
- Persists structured telemetry: `(timestamp, person_position, person_id)`.

### 3. Perspective Homography & Density Heatmaps
- Applies $3 \times 3$ homography transformation matrices to correct perspective distortion (near camera vs. far camera).
- Calculates real-world density ($ppl/m^2$) across defined zones and renders spatial density heatmaps.

### 4. Explainable Multi-Factor Risk Engine
- Predicts stampede hazards and produces human-understandable risk rationales.
- Combines 4 rolling temporal indicators: Density Ratio, Velocity Deficit, Directional Chaos, and Surge Growth.

### 5. Enterprise Security & RBAC
- **Supabase Auth JWT**: Enforces signature validation on all incoming bearer tokens.
- **Role-Based Access Control**:
  - `ADMIN`: Full camera lifecycle (`POST /cameras`, `PUT /cameras/{id}`), system configuration, alert management.
  - `OPERATOR`: Dashboard overview, live camera streams, heatmap viewer, alert resolution (`PUT /alerts/{id}/resolve`). Attempting to register cameras yields `HTTP 403 Forbidden`.
- **Duplicate Alert Protection**: PostgreSQL partial unique index ensures only **one active alert** can exist per camera and zone simultaneously, preventing notification floods.

### 6. Production Hardening & Rate Limiting
- **SlowAPI**: Enforces `100 requests/minute per IP` on public endpoints (`/health`) and `300 requests/minute per user` on authenticated APIs. Internal AI workers bypass limits via `X-Service-Token`.
- **CORS Hardening**: Wildcard origin `*` is strictly forbidden in production.

---

## 📐 Mathematical Foundations

### 1. Velocity Calculation (Wall-Clock Distance Over Time)
For tracked pedestrian $i$ with positions $(x_1, y_1)$ at $t_1$ and $(x_2, y_2)$ at $t_2$:
$$\text{Speed}_i = \frac{\sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}}{t_2 - t_1} \quad \left[\frac{\text{pixels}}{\text{second}}\right]$$

### 2. Temporal Crowd Growth Rate
Calculated over a rolling wall-clock window $\Delta t = t_{\text{curr}} - t_{\text{prev}}$:
$$\text{Growth Rate} = \frac{N_{\text{current}} - N_{\text{previous}}}{N_{\text{previous}} \times \Delta t} \quad \left[\frac{\%}{\text{second}}\right]$$
*Example: An influx from 200 people to 240 people over a 10-second window represents an active growth rate of $+2.0\%/\text{second}$ ($+20\%$ total).*

### 3. Explainable Safety Risk Score
$$\text{Risk Score} = 100 \times \left( w_d \cdot f_{\text{density}} + w_v \cdot f_{\text{velocity}} + w_c \cdot f_{\text{chaos}} + w_g \cdot f_{\text{growth}} \right)$$
- **Density Factor** ($f_{\text{density}}$): Current density vs. critical threshold ($4.0\text{ ppl}/m^2$).
- **Velocity Factor** ($f_{\text{velocity}}$): Sharp drops in pedestrian speed indicate flow constriction or tripping.
- **Chaos Factor** ($f_{\text{chaos}}$): Variance in pedestrian movement vectors (multi-directional panic).
- **Growth Factor** ($f_{\text{growth}}$): Rapid population surges into enclosed choke points.

---

## 👥 Role-Based Access Control (RBAC) Matrix

| Endpoint | Method | `ADMIN` Role | `OPERATOR` Role | Public / Unauth |
| :--- | :---: | :---: | :---: | :---: |
| `/health` | GET | Allowed | Allowed | Allowed (100 req/min) |
| `/dashboard/overview` | GET | Allowed | Allowed | Denied (401) |
| `/cameras` | GET | Allowed | Allowed | Denied (401) |
| `/cameras` | POST | **Allowed** | **Forbidden (403)** | Denied (401) |
| `/cameras/{id}` | PUT | **Allowed** | **Forbidden (403)** | Denied (401) |
| `/alerts` | GET | Allowed | Allowed | Denied (401) |
| `/alerts/{id}/resolve` | PUT | Allowed | **Allowed** | Denied (401) |
| `/demo/scenario` | POST | Allowed | Allowed | Denied (401) |

---

## 📂 Project Directory Structure

```
CrowdEye/
├── .github/                      # CI/CD workflows
├── .gitignore                    # Production git ignore configuration
├── docker-compose.yml            # Multi-service deployment (Backend + AI Worker)
├── Dockerfile.backend            # Production image for FastAPI API server
├── Dockerfile.ai                 # Production image for AI inference worker
├── README.md                     # Project master documentation
│
├── ai/                           # Core AI Algorithm Libraries
│   ├── detection/                # YOLOv8n detector wrapper & model loaders
│   ├── tracking/                 # DeepSORT tracker, track history & movement kinematics
│   ├── density/                  # Homography matrix transforms & zone density
│   └── risk/                     # Explainable multi-factor risk scoring engine
│
├── ai_worker/                    # Decoupled AI Inference Worker Microservice
│   ├── config.py                 # Worker configuration & environment bindings
│   ├── inference.py              # UnifiedInferenceEngine singleton
│   ├── video_queue.py            # Multi-stream bounded ingestion queue
│   └── worker.py                 # Async worker process & telemetry publisher
│
├── backend/                      # FastAPI Application Gateway
│   ├── app/
│   │   ├── auth/                 # Supabase JWT validation & require_role RBAC
│   │   ├── config/               # Settings, SlowAPI rate limiter & rotating logger
│   │   ├── database/             # Supabase PostgreSQL client connection
│   │   ├── routes/               # REST routers (cameras, alerts, health, demo, dashboard)
│   │   ├── services/             # Domain logic (camera, alert, tracking, analytics)
│   │   └── main.py               # Application factory, middleware & startup hooks
│   └── requirements.txt          # Python backend dependencies
│
├── database/
│   └── migrations/               # PostgreSQL Database Migrations (001 - 008)
│       ├── 001_initial_schema.sql
│       ├── 002_tracking_schema.sql
│       ├── 003_tracking_jobs.sql
│       ├── 004_density_schema.sql
│       ├── 005_risk_schema.sql
│       ├── 006_alerts.sql
│       ├── 007_camera_update.sql
│       └── 008_production_indexes.sql
│
├── docs/                         # Extended Architectural & Deployment Guides
│   └── deployment.md             # Cloud deployment steps (Vercel, Railway, AWS, Supabase)
│
├── frontend/                     # Security Control Room Operations Interface
│   ├── css/                      # Responsive CSS & glassmorphic design system
│   ├── js/                       # Realtime WebSocket handlers, Chart.js & state
│   └── pages/
│       ├── dashboard.html        # Main Control Room UI + Hackathon Live Demo Controller
│       ├── cameras.html          # Camera management & video feed grid
│       ├── alerts.html           # Incident audit log & resolution interface
│       └── analytics.html        # 1-minute temporal bucket charts & comparisons
│
├── logs/                         # Rotating application log outputs
│   └── .gitkeep
├── scratch/                      # Automated benchmark suites & tests
│   ├── test_phase6_pipeline.py   # RBAC & alert workflow verification
│   └── test_phase7_performance.py# Realistic multi-camera capacity & 100-user stress suite
└── videos/                       # Test video directory
    └── .gitkeep
```

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python**: 3.10 or 3.11
- **Node.js**: 18+ (optional, for Vercel CLI)
- **Supabase Project**: Free or Pro PostgreSQL instance

### 1. Clone & Configure Environment
```bash
git clone https://github.com/SanskarEdhate/CrowdEye.git
cd CrowdEye

# Create environment file from template
cp .env.example .env
```

Configure `.env` with your Supabase credentials:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
ENVIRONMENT=production
FRONTEND_URL=https://crowdeye.vercel.app
DEMO_MODE=false
```

### 2. Execute Database Migrations
Execute SQL migrations in sequential order (`001` through `008`) inside your **Supabase SQL Editor**:
- [001_initial_schema.sql](database/migrations/001_initial_schema.sql)
- [006_alerts.sql](database/migrations/006_alerts.sql) (Alerts schema, Profiles RBAC table)
- [007_camera_update.sql](database/migrations/007_camera_update.sql) (Camera status & zone config)
- [008_production_indexes.sql](database/migrations/008_production_indexes.sql) (High-speed query indexes)

### 3. Launch FastAPI Backend
```bash
cd backend
python -m venv venv
# Activate virtualenv:
# Windows: venv\Scripts\activate | Linux/macOS: source venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Test health: `curl http://localhost:8000/health`

### 4. Launch AI Worker Service
In a separate terminal:
```bash
cd ai_worker
python worker.py
```

### 5. Open Operator Dashboard
Serve `frontend/pages/` using any static web server:
```bash
python -m http.server 3000 --directory frontend/pages
```
Navigate to `http://localhost:3000/dashboard.html` in your web browser.

---

## 🐳 Docker Deployment

CrowdEye AI is fully containerized for multi-service cloud execution without local database setup (Supabase remains a managed cloud service):

```bash
# Build and run backend and AI worker containers in detached mode
docker-compose up --build -d

# Verify running services
docker-compose ps

# Tail live application logs
docker-compose logs -f
```

---

## 📊 Empirical Performance Benchmarks

Results obtained from the realistic performance suite ([`scratch/test_phase7_performance.py`](scratch/test_phase7_performance.py)):

| Test Suite | Metric Measured | Production Target | Benchmark Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Test 1: Single Camera AI** | Inference FPS & Latency | $> 5.0\text{ FPS}$ | **$15.3\text{ FPS}$** ($65.47\text{ ms}$ avg) | **PASS** |
| **Test 2: 5-Camera Simulation** | Concurrent Ingestion Delay | $< 350\text{ ms}$ | **$306.62\text{ ms}$** delay ($15.6\text{ FPS}$ total) | **PASS** |
| **Test 3: 100 Dashboard Users** | Concurrent Request Latency | 100% Handled | **$384.40\text{ ms}$** avg, **$791.69\text{ ms}$** p95 | **PASS** |
| **Test 4: System Health & Limits** | Rate Limiter Burst Guard | HTTP 429 | Triggered exactly at request #100 | **PASS** |

---

## 🎭 Hackathon Demo Script & Flow

CrowdEye AI includes a built-in **Live Demo Controller** located directly at the top of the Security Dashboard (`dashboard.html`):

```
+----------------------------------------------------------------------------------------------------+
| 🔴 HACKATHON LIVE DEMO CONTROLLER: [🟢 Normal Flow]  [🟡 Elevated Crowd]  [🔴 Critical Surge] [↺ Reset] |
+----------------------------------------------------------------------------------------------------+
```

### 8-Step Demonstration Script:
1. **Operator Sign-In**: Open `dashboard.html`. Select `OPERATOR` role.
2. **Dashboard Review**: Note initial green status: 4 active cameras, 0 active alerts, normal crowd flow.
3. **CCTV Stream Grid**: Navigate through the multi-camera grid showing live bounding boxes, zone IDs, and track IDs.
4. **Trigger Surge**: Click **`[🔴 Critical Surge]`** on the Live Demo Controller.
5. **AI Detection & Analysis**: The Explainable Risk Engine calculates risk jump to **92.5** based on surge density ($>4.5\text{ ppl}/m^2$) and velocity collapse.
6. **Heatmap Illumination**: The Zone C spatial heatmap turns red.
7. **Instant Safety Alarm**: Audio chime sounds and a **`CRITICAL`** red alert banner appears with duplicate suppression.
8. **Incident Resolution**: Click **`[Resolve Incident]`**. The alert updates to `RESOLVED` in Supabase, broadcasts `alert_resolved` across all WebSocket clients, and clears the alert banner.

---

## 📡 API Specification

### Health & Monitoring
- `GET /health`: Returns system status (`api`, `database`, `ai_worker`, `model_status`, `demo_mode`). Rate limited to `100 req/min`.

### Cameras (`/cameras`)
- `GET /cameras`: List all registered CCTV cameras, locations, and live risk states.
- `POST /cameras`: Register a new camera stream (**ADMIN only**, returns 403 for `OPERATOR`).
- `PUT /cameras/{id}`: Modify camera status (`ACTIVE`, `MAINTENANCE`, `OFFLINE`) or update homography matrix (**ADMIN only**).

### Incident Alerts (`/alerts`)
- `GET /alerts`: Retrieve active and historical alerts with optional status filters (`ACTIVE`, `RESOLVED`).
- `PUT /alerts/{id}/resolve`: Resolve an active hazard alarm (**ADMIN** and **OPERATOR**).
- `POST /alerts/evaluate`: Internal engine evaluation endpoint.

### Dashboard & Analytics
- `GET /dashboard/overview`: High-level metrics for control room metric cards.
- `GET /analytics/timeline?window_minutes=30`: Aggregated 1-minute temporal buckets for people count and risk curves.
- `POST /demo/scenario`: Injects simulated demonstration events (`low`, `medium`, `critical`).
- `WS /ws/realtime`: Real-time WebSocket event subscription bus (`alerts`, `camera_status`, `risk_update`).

---

## 🛡️ License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
Designed and engineered for crowd safety at major sports, cultural, and civic gatherings.
