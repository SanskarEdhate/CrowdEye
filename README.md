# CrowdEye AI - Real-time Crowd Safety & Security Operations Platform

> **Intelligent Multi-Camera Telemetry, Explainable AI Risk Prediction & Control Room Management for Large Public Events**

CrowdEye AI is an enterprise-grade crowd safety platform engineered for stadiums, music festivals, transit hubs, and massive public gatherings. It analyzes camera feeds in real time, computes pedestrian density and movement vectors, predicts stampede hazards before escalation, and provides an operator control room dashboard for rapid incident response.

---

## System Architecture

```
Camera (CCTV / RTSP Stream)
       ↓
   AI Engine (YOLOv8 Detection + DeepSORT Tracking + Homography Density)
       ↓
  Risk Engine (10-Second Temporal Rolling Window: Density, Speed, Chaos, Growth)
       ↓
 Alert Manager (Threshold Safety Rules + Duplicate Protection Constraint)
       ↓
Operator Dashboard (Realtime WebSocket Subscriptions + Camera Grid + Alert Resolution)
```

---

## Role-Based Access Control (RBAC)

CrowdEye AI implements strict role-based authorization backed by Supabase Auth and database Row Level Security (RLS):

| Role | Dashboard Permissions | Restricted Actions |
| :--- | :--- | :--- |
| **ADMIN** | • View security dashboard & telemetry<br>• Register new CCTV cameras (`POST /cameras`)<br>• Update camera configuration & status (`PUT /cameras/{id}`)<br>• Manage and resolve all alerts | None |
| **OPERATOR** | • View security control room dashboard<br>• Monitor camera feeds & live density<br>• View active alerts and historical audit logs<br>• Resolve active incident alerts (`PUT /alerts/{id}/resolve`) | • Registering new cameras (HTTP 403 Forbidden)<br>• Modifying camera properties or status (HTTP 403 Forbidden) |

---

## Alert Workflow & Safety Rules

Alerts are generated directly from the Explainable Risk Engine evaluations:

```
Risk Score (0 - 100)
    ├── Score <= 30  (LOW)      : Normal crowd flow (No alert)
    ├── Score 31-60  (MEDIUM)   : Monitoring only (No alert created)
    ├── Score 61-80  (HIGH)     : WARNING alert created
    └── Score 81-100 (CRITICAL) : CRITICAL alert created
```

### Duplicate Protection
A database constraint and partial unique index enforce that only **one active alert** can exist per camera and zone simultaneously:
```sql
CREATE UNIQUE INDEX idx_active_alert_unique
ON public.alerts (camera_id, COALESCE(zone_id, '00000000-0000-0000-0000-000000000000'::uuid))
WHERE status = 'ACTIVE';
```
If subsequent risk evaluations occur while an alert is active, duplicate inserts are suppressed and the existing alert's score is updated.

### Alert Status Lifecycle:
- `ACTIVE`: Incident requires operator attention. Displayed on Dashboard & Alert Panel.
- `ACKNOWLEDGED`: Operator has marked the alarm for dispatch.
- `RESOLVED`: Incident mitigated. Operator clicks "Resolve", setting `status='RESOLVED'` and stamping `resolved_at`. Broadcasts `alert_resolved` over WebSocket.

---

## API Reference

### 1. Dashboard Overview
- `GET /dashboard/overview`
  - Accessible to: `ADMIN`, `OPERATOR`
  - Returns:
    ```json
    {
      "total_cameras": 10,
      "active_alerts": 3,
      "high_risk_zones": 2,
      "detected_people": 2500
    }
    ```

### 2. Camera Management
- `POST /cameras`: Register new CCTV camera (**ADMIN only**, returns 403 for `OPERATOR`)
- `GET /cameras`: Retrieve all cameras with status and live metrics (`ADMIN` + `OPERATOR`)
- `PUT /cameras/{id}`: Update camera location, status (`ACTIVE`, `MAINTENANCE`, `OFFLINE`), or zone config (**ADMIN only**)

### 3. Alert Management
- `GET /alerts`: Retrieve active alerts and history with status filter (`ADMIN` + `OPERATOR`)
- `PUT /alerts/{id}/resolve`: Resolve an active incident alert (`ADMIN` + `OPERATOR`)
- `POST /alerts/evaluate`: Evaluate risk input against safety rules

### 4. Aggregated Analytics (1-Minute Temporal Buckets)
- `GET /analytics/timeline?window_minutes=30`: Aggregates 5-second raw crowd telemetry into 1-minute averages for headcount and risk timelines.
- `GET /analytics/zones`: Compares multi-zone metrics across headcount, density, and risk scores.

### 5. Realtime WebSocket Subscriptions
- `ws://localhost:8000/ws/realtime`
  - Subscriptions: Send `{"action": "subscribe", "topic": "alerts"}` or `{"action": "subscribe", "topic": "camera:{id}"}`
  - Events Broadcast:
    - `alert_created`: High/Critical risk event triggered
    - `alert_resolved`: Operator resolved incident
    - `camera_status`: Camera status changed or created
    - `risk_update`: Live risk telemetry update

---

## Database Migrations

All schema definitions are located in `database/migrations/`:
- `001_initial_schema.sql`: Core schema (users, events, cameras, crowd_logs, alerts)
- `002_tracking_schema.sql`: Person tracking trajectories
- `003_tracking_jobs.sql`: DeepSORT asynchronous job management
- `004_density_schema.sql`: Zone density and spatial homography
- `005_risk_schema.sql`: Temporal risk evaluation and explainability logs
- `006_alerts.sql`: Alerts table with status lifecycle, duplicate active protection, profiles table, and RLS policies
- `007_camera_update.sql`: Modifies existing cameras table with `location`, `status DEFAULT 'ACTIVE'`, and `zone_config JSONB`

---

## Frontend Web Applications

Located in `frontend/pages/`:
- **`dashboard.html`**: Security Control Room Operations Dashboard featuring:
  - 4 Overview Metric Cards (Active Cameras, Detected People, Active Alerts, High Risk Zones)
  - Real-time Camera Grid Cards with status, people count, density, and risk badges
  - Active Alert Panel with instant "Resolve Incident" action
  - Role switcher (ADMIN vs OPERATOR)
- **`cameras.html`**: Camera Management Portal (Add camera, view live feed grid, toggle operating status)
- **`alerts.html`**: Incident Alarms & Historical Audit Table (filter by status, view timestamps, and resolve)
- **`analytics.html`**: Interactive Chart.js Timelines (People Count Timeline, Risk Score Timeline, and Zone Comparison backed by 1-minute aggregation)

---

## Verification & Testing

Run the automated test suite covering all 5 Phase 6 scenarios:
```bash
python scratch/test_phase6_pipeline.py
```
Test suite validates:
1. Risk score 90 -> Critical alert created
2. Duplicate alert generation -> Only one active alert (duplicate suppressed)
3. Operator login -> Can resolve alerts
4. Operator camera creation -> Permission denied (HTTP 403 Forbidden)
5. Multiple cameras -> Camera grid updates & overview metrics
