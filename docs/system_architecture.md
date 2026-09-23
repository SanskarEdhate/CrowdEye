# CrowdEye AI - End-to-End System Architecture

This document specifies the technical blueprint for the **CrowdEye AI** platform, describing the data flow, security model, and structural boundaries across all tiers.

---

## 1. High-Level Architecture Diagram

```
+-------------------------------------------------------------+
|                      PRESENTATION TIER                      |
|                  Vanilla HTML5 / CSS3 / JS                  |
|  - Real-time DeepSORT Canvas (Bounding Boxes, Trajectories) |
|  - Telemetry Dashboard (Active Tracks, Direction, Velocity) |
|  - Leaflet GIS, Chart.js Analytics                         |
+------------------------------+------------------------------+
                               |
                               | REST Upload / Status Polling + WebSocket (/ws/tracking)
                               v
+-------------------------------------------------------------+
|                     APPLICATION TIER                        |
|                     FastAPI + Uvicorn                       |
|   - POST /tracking/start, GET /tracking/status/{job_id}     |
|   - GET /tracking/result/{job_id}, WebSocket Streaming      |
|   - TrackingWorker BackgroundTasks Engine                   |
+------------------------------+------------------------------+
                               |
                               | Spawns DeepSORT Tracking Worker
                               v
+-------------------------------------------------------------+
|                 AI PERCEPTION & TRACKING WORKER (Phase 3)   |
|  1. OpenCV Video Frame Reader                               |
|  2. YOLOv8 Detection (Class 0: Person)                      |
|  3. DeepSORT Appearance-based Multi-Object Tracker          |
|     (MobileNet Embedder, max_age=30, n_init=2)              |
|  4. TrackHistory (10-second Rolling Spatiotemporal Memory)  |
|  5. MovementAnalyzer (8-Way Direction + px/s Velocity)      |
+------------------------------+------------------------------+
                               |
                               | Telemetry Ingestion (5s Batches)
                               v
+-------------------------------------------------------------+
|                        DATA TIER                            |
|                   Supabase PostgreSQL                       |
|   - tracking_jobs (Job Status, Progress, Total Unique)      |
|   - person_tracking (x, y, direction, speed, timestamp)     |
|   - crowd_logs, users, events, cameras, alerts + RLS        |
+-------------------------------------------------------------+
```

---

## 1.1 Video Ingestion & Tracking Pipeline Flow (Phase 2 & 3)

```
[ CCTV Video / Recording (.mp4) ]
            |
            v
[ FastAPI: POST /tracking/start ]
            |
            v
[ TrackingService: Insert tracking_jobs (status: 'queued') ]
            |
            v
[ FastAPI BackgroundTasks: TrackingWorker ]
            |
            v
[ Frame Extraction: cv2.VideoCapture ]
            |
            v
[ YOLOv8: Person Detections (Class 0, Conf >= 0.45) ]
            |
            v
[ DeepSORT Tracker: Feature Extraction (MobileNet) + Kalman Filter ]
            |
            v
[ TrackHistory: In-memory coordinate buffer (10s sliding window) ]
            |
            v
[ MovementAnalyzer: Direction (8-way) + Relative Speed (px/s) ]
            |
      +-----+-------------------------------+
      |                                     |
      v (Real-time Broadcast)               v (Batched every 5s)
[ TrackingConnectionManager ]        [ TrackingService.batch_insert() ]
      |                                     |
      v                                     v
[ WebSocket: /ws/tracking/{job_id} ] [ Supabase: person_tracking ]
      |                                     |
      v                                     v
[ Frontend HTML5 Canvas (Visualizer) ] [ Supabase: tracking_jobs ('completed') ]
```

---

## 1.2 Phase 4: Crowd Density & Zone Heatmap Pipeline Flow

```
[ CCTV Video / Recording (.mp4) ]
            |
            v
[ FastAPI: POST /density/start ]
            |
            v
[ DensityService: Insert density_jobs (status: 'queued') ]
            |
            v
[ FastAPI BackgroundTasks: DensityWorker ]
            |
            v
[ YOLOv8 Person Detection (COCO Class 0) ]
            |
            v
[ DeepSORT Multi-Object Tracking (MobileNet Embedder) ]
            |
            v
[ Person Centroid Extraction: (cx, cy) ]
            |
            v
[ Camera Perspective Correction (OpenCV Homography Matrix) ]
            |
            v
[ ZoneManager: Point-in-Polygon Spatial Mapping (Zones A - F) ]
            |
            v
[ DensityEstimator: normalized score = people_count / zone_capacity ]
            |
            v
[ 4-Tier Classification: LOW (0-40%), MEDIUM (40-70%), HIGH (70-90%), CRITICAL (90%+) ]
            |
      +-----+-------------------------------+
      |                                     |
      | (If Density > 0.70 or Low Conf)    | (Every Frame)
      v                                     v
[ Optional CSRNet Verification ]     [ Dynamic HeatmapGenerator (Gaussian Matrix) ]
      |                                     |
      +-----------------+-------------------+
                        |
                        +-------------------------------+
                        |                               |
                        v (5-Second Batches)            v (Result Poll)
          [ Supabase: crowd_density ]      [ GET /density/result/{job_id} ]
                        |                               |
                        v                               v
          [ Supabase: density_jobs ]        [ Frontend Dashboard: Zone Cards & Canvas Heatmap ]
```


```
[ CCTV Video / Recording ]
            |
            v
[ FastAPI: POST /detection/video ]
            |
            v
[ JobService: Create job_id, Status: queued ]
            |
            v
[ FastAPI BackgroundTasks Worker ]
            |
            v
[ OpenCV cv2.VideoCapture (Headless Frame Reader) ]
            |
            v
[ YOLOv8 Person Detection (COCO Class 0, Conf >= 0.45) ]
            |
            v
[ Aggregation: Headcount, Avg People, Max People, Duration ]
            |
            v
[ Supabase crowd_logs Insertion (status: 'DETECTED') ]
            |
            v
[ Frontend Client Status Polling & Result Display ]
```

---

## 2. Core Components & Tier Breakdown

### 2.1 Frontend Tier (Client-Side)
- **Role**: Operator interface for command centers and security guards on duty.
- **Technologies**: Vanilla HTML5, CSS3, ES6 JavaScript, Chart.js, Leaflet.js.
- **Functionality**:
  - Live metric visualization: Total headcount, area density ($\text{ppl/m}^2$), risk index ($0.0 - 1.0$), and active alert counters.
  - Interactive GIS venue layout: Leaflet map representing CCTV coverage radiuses, heat distribution, and emergency exit routes.
  - Direct communication via the Fetch API with the FastAPI backend.
  - Direct query of read-only telemetry from Supabase using the public `anonKey` with **Row Level Security (RLS)** constraints.

### 2.2 Application Backend Tier (FastAPI)
- **Role**: API gateway, operational business logic, alert aggregation, and client validation.
- **Technologies**: Python 3.11+, FastAPI, Uvicorn, Pydantic, Python-Dotenv.
- **Functionality**:
  - Exposes REST endpoints (`/api/v1/crowd/status`, `/api/v1/alerts`, `/api/v1/events`).
  - CORS middleware allowing secure cross-origin requests from distributed operator terminals.
  - Securely loads and protects private credentials (`SUPABASE_SERVICE_KEY`) to interact with Supabase with administrative rights.
  - Verifies database health and manages alert dispatch logic.

### 2.3 Database Tier (Supabase PostgreSQL)
- **Role**: Persistent transactional storage and real-time subscription engine.
- **Tables**:
  1. `users`: Operator profiles and role assignments.
  2. `events`: Monitored venues, dates, and operational phases.
  3. `cameras`: Registered video capture sources mapped to venue zones.
  4. `crowd_logs`: Time-series crowd headcount, density, and risk telemetry.
  5. `alerts`: Security alarms triggered by high-density surges and stampede indicators.
- **Security & RLS**:
  - All 5 tables have Row Level Security enabled.
  - Public anonymous users are blocked from mutating data.
  - Authenticated operators can read events, cameras, crowd telemetry, and alerts.
  - Only the backend service key can write to `crowd_logs` and generate `alerts`, preventing unauthorized client data tampering.

### 2.4 AI Engine Tier (Phase 2 Roadmap)
- **Role**: Video feed ingestion, deep learning computer vision, trajectory tracking, and automated risk scoring.
- **Components**:
  - **YOLOv8**: Real-time object detection for individual person localization.
  - **DeepSORT**: Multi-target tracking algorithm preserving person IDs across frames to measure flow velocity and directional anomalies.
  - **CSRNet**: Congested Scene Recognition Network utilizing dilated convolutions to generate high-fidelity crowd density heatmaps in extremely crowded scenes.
  - **Risk Assessment Model**: Evaluates sudden density accumulation ($> 3.5 \text{ ppl/m}^2$), counter-flow collisions, and exit bottlenecking. Upon detecting threshold breaches, the worker communicates with the backend or directly writes alerts to Supabase using the service role key.

---

## 3. Data Flow Progression

1. **Video Ingestion (Phase 2)**: CCTV cameras stream RTSP feeds to the AI Worker node.
2. **Inference Execution**: YOLOv8 and CSRNet compute instantaneous crowd counts and density maps.
3. **Telemetry Ingestion**: The AI inference pipeline packages results into a structured payload and inserts them into `crowd_logs` via the Supabase Service Role client.
4. **Alert Generation**: If risk scores exceed critical thresholds ($>0.75$), an alert record is created in the `alerts` table.
5. **Real-time Propagation**: Supabase broadcasts the new alert to connected operator dashboards.
6. **Command Dashboard**: The operator dashboard updates the metric cards, plots new density points on Chart.js, updates the Leaflet zone markers, and notifies dispatchers.
