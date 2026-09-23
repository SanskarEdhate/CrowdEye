# CrowdEye AI - End-to-End System Architecture

This document specifies the technical blueprint for the **CrowdEye AI** Security Operations Platform, describing data pipelines, AI models, security enforcement, alert management, and dashboard visualization.

---

## 1. System Operations Pipeline Flow (Phase 6)

```
        +-------------------------------------+
        |               Camera                |
        |  (RTSP Stream / CCTV Video Feed)    |
        +------------------+------------------+
                           |
                           v
        +-------------------------------------+
        |              AI Engine              |
        |   - YOLOv8 Person Detection         |
        |   - DeepSORT Multi-Object Tracker   |
        |   - Perspective Homography Correct. |
        |   - Zone Density Matrix (A - F)     |
        +------------------+------------------+
                           |
                           v
        +-------------------------------------+
        |             Risk Engine             |
        |   - 10-Second Temporal Rolling Window
        |   - Normalized Features (D, S, C, G)|
        |   - Deterministic Formula (0-100)   |
        |   - Explainability Reason Generator |
        +------------------+------------------+
                           |
                           v
        +-------------------------------------+
        |            Alert Manager            |
        |   - LOW: No alert                   |
        |   - MEDIUM: Monitoring only         |
        |   - HIGH: WARNING alert             |
        |   - CRITICAL: CRITICAL alert        |
        |   - (camera_id, zone_id) Dedup      |
        +------------------+------------------+
                           |
                           v
        +-------------------------------------+
        |         Operator Dashboard          |
        |   - Realtime WebSocket Subscriptions|
        |   - Camera Telemetry Grid (Status)  |
        |   - Active Alarm Mitigation Panel   |
        |   - Incident Resolution Action      |
        |   - 1-Minute Aggregated Analytics   |
        +-------------------------------------+
```

---

## 2. High-Level Component Architecture

```
+---------------------------------------------------------------------------------+
|                               PRESENTATION TIER                                 |
|               Vanilla HTML5 / CSS3 / ES6 JavaScript / Chart.js                  |
|  - dashboard.html: Overview Cards, Camera Grid, Active Incident Alert Panel     |
|  - cameras.html: CCTV Node Registration, Zone & Location Mapping, Status Switch |
|  - alerts.html: Audit History Log, Severity Filtering, Incident Resolution      |
|  - analytics.html: 1-Minute Aggregated Headcount & Risk Timelines, Zone Analysis|
+---------------------------------------+-----------------------------------------+
                                        |
                                        | REST APIs + WebSocket (/ws/realtime)
                                        v
+---------------------------------------------------------------------------------+
|                               APPLICATION TIER                                  |
|                             FastAPI + Uvicorn                                   |
|   - Authentication & RBAC: ADMIN vs OPERATOR Roles                              |
|   - Dashboard: GET /dashboard/overview                                          |
|   - Cameras: POST /cameras (Admin), GET /cameras, PUT /cameras/{id} (Admin)     |
|   - Alerts: GET /alerts, PUT /alerts/{id}/resolve                               |
|   - Analytics: GET /analytics/timeline (1-min avg), GET /analytics/zones        |
|   - WebSocket Manager: Realtime topic subscriptions (camera, zone, alerts)      |
+---------------------------------------+-----------------------------------------+
                                        |
                                        v
+---------------------------------------------------------------------------------+
|                             AI & RISK PIPELINE                                  |
|  1. Detection: YOLOv8 Person Detection (COCO Class 0)                           |
|  2. Tracking: DeepSORT with MobileNet Embedder & Kalman Filter                  |
|  3. Density: Point-in-polygon mapping + Perspective Homography + Heatmaps       |
|  4. Risk: Score = 0.40*Density + 0.25*Speed + 0.20*Chaos + 0.15*Growth          |
|  5. Alert Service: Rule-based thresholding, duplicate suppression, dispatch     |
+---------------------------------------+-----------------------------------------+
                                        |
                                        v
+---------------------------------------------------------------------------------+
|                                 DATA TIER                                       |
|                            Supabase PostgreSQL                                  |
|   - cameras: id, event_id, camera_name, zone, stream_url, location, status,     |
|              zone_config                                                        |
|   - alerts: id, camera_id, zone_id, risk_score, alert_level, message, status,   |
|             created_at, resolved_at + Partial UNIQUE Index for duplicate prot.  |
|   - profiles: id, role ('ADMIN', 'OPERATOR') + Row Level Security (RLS)         |
|   - crowd_risk, crowd_density, person_tracking, crowd_logs, events, users       |
+---------------------------------------------------------------------------------+
```

---

## 3. Role-Based Access Control (RBAC) & Security Architecture

The platform enforces two distinct operational roles backed by Supabase Auth and database RLS:

| Role | Permissions | Restricted Actions |
| :--- | :--- | :--- |
| **ADMIN** | • Register new CCTV cameras (`POST /cameras`)<br>• Update camera configuration & status (`PUT /cameras/{id}`)<br>• View dashboard overview and camera feeds<br>• Manage and resolve all alerts | None |
| **OPERATOR** | • View security dashboard and live metrics<br>• Monitor camera feeds and zone statuses<br>• View active alerts and audit history<br>• Resolve active incident alerts (`PUT /alerts/{id}/resolve`) | • Adding cameras (403 Forbidden)<br>• Modifying camera properties or status (403 Forbidden) |

### Row Level Security (RLS) Implementation:
- `public.cameras`:
  - `SELECT`: Permitted for all authenticated users (`ADMIN` and `OPERATOR`).
  - `INSERT`, `UPDATE`, `DELETE`: Restricted to `ADMIN` via `public.is_admin()` security definer function.
- `public.alerts`:
  - `SELECT`: Permitted for all authenticated users.
  - `UPDATE`: Permitted for authenticated users when modifying status to `RESOLVED` or `ACKNOWLEDGED`.
  - `ALL`: Full access granted to `service_role`.

---

## 4. Alert Workflow & Duplicate Protection Architecture

```
[ Risk Engine Score ]
          |
          +---> Score <= 30 (LOW): No Alert
          |
          +---> Score 31 - 60 (MEDIUM): Monitoring Only (No Alert)
          |
          +---> Score 61 - 80 (HIGH): WARNING Alert Generated
          |
          +---> Score 81 - 100 (CRITICAL): CRITICAL Alert Generated
                         |
                         v
          [ Duplicate Protection Check ]
          Query: SELECT * FROM alerts WHERE (camera_id, zone_id) AND status = 'ACTIVE'
                         |
          +--------------+--------------+
          |                             |
          | (Active Alert Exists)       | (No Active Alert)
          v                             v
[ Suppress Duplicate Insert ]   [ Insert New Alert Record ]
[ Update Active Risk Score  ]   - id: UUID
                                - alert_level: WARNING / CRITICAL
                                - status: 'ACTIVE'
                                        |
                                        v
                                [ Realtime WebSocket Broadcast ]
                                - event: 'alert_created'
                                - topic: 'alerts'
                                        |
                                        v
                                [ Control Room Alert Panel Update ]
                                        |
                                        v (Operator presses "Resolve")
                                [ PUT /alerts/{id}/resolve ]
                                - status -> 'RESOLVED'
                                - resolved_at -> timestamp
                                - event: 'alert_resolved'
```

### Database Duplicate Protection:
PostgreSQL partial unique index enforces database-level integrity:
```sql
CREATE UNIQUE INDEX idx_active_alert_unique
ON public.alerts (camera_id, COALESCE(zone_id, '00000000-0000-0000-0000-000000000000'::uuid))
WHERE status = 'ACTIVE';
```

---

## 5. Realtime WebSocket Topic Subscriptions

Endpoints:
- `/ws/realtime`: Main subscription and event broadcast hub.
- `/ws/alerts`: Dedicated alert notification stream.
- `/ws/tracking`: Video telemetry and person movement stream.

Supported Topics:
- `camera:{camera_id}`: Stream events specific to a physical camera.
- `zone:{zone_id}`: Stream events specific to a spatial sector.
- `alerts`: Stream all alert creations and resolutions across the entire venue.

Event Schemas:
```json
// Event: alert_created
{
  "event": "alert_created",
  "alert_id": "d0ef82fe-e4ea-405a-a49e-aa1b3894553c",
  "camera": "Gate North Turnstiles",
  "zone": "Zone A",
  "level": "CRITICAL",
  "message": "High crowd risk detected in Zone Zone A",
  "risk_score": 88.5,
  "created_at": "2026-09-23T12:00:00Z"
}

// Event: alert_resolved
{
  "event": "alert_resolved",
  "alert_id": "d0ef82fe-e4ea-405a-a49e-aa1b3894553c",
  "status": "RESOLVED",
  "resolved_at": "2026-09-23T12:05:12Z",
  "resolved_by": "operator"
}

// Event: camera_status
{
  "event": "camera_status",
  "camera_id": "11111111-1111-1111-1111-111111111101",
  "status": "MAINTENANCE",
  "camera_name": "Gate North Turnstiles"
}
```

---

## 6. Analytics 1-Minute Aggregation Pipeline

Raw telemetry gathered at 5-second intervals from YOLOv8, DeepSORT, and the Density Homography Engine is aggregated into 1-minute averages by `AnalyticsService`:
1. Raw logs are queried across a sliding time window (15, 30, or 60 minutes).
2. Data is bucketed into `YYYY-MM-DDTHH:MM:00Z` timestamps.
3. For each bucket, the service computes:
   - Average headcount (`avg_people_count`)
   - Average spatial density (`avg_density`)
   - Average composite risk score (`avg_risk_score`)
4. Served via `GET /analytics/timeline` to Chart.js for responsive multi-timeline rendering.
