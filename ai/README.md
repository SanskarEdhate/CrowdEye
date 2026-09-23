# CrowdEye AI - Artificial Intelligence Module Specification

> **Phase 2 Implementation Roadmap (Reserved for Future Development)**

---

## 1. Scope & Status Notice

> **IMPORTANT**: In compliance with Phase 1 constraints, **NO AI models are implemented yet**. This directory serves as the architectural and interface contract for the Phase 2 deep learning pipeline.

---

## 2. Planned AI Modules

### 2.1 YOLOv8 (Person Detection)
- **Role**: Object detection specialized for human bounding boxes in moderate-to-high resolution camera feeds.
- **Model**: `yolov8n.pt` / `yolov8s.pt` (Ultralytics) optimized for high inference throughput (>45 FPS on CUDA GPUs).
- **Output**: Bounding coordinates `[x1, y1, x2, y2]`, confidence score, and person class ID.

### 2.2 DeepSORT (Movement Tracking & Flow Analysis)
- **Role**: Preserves object identity across temporal video frames using Kalman filters and visual deep appearance descriptors.
- **Metrics Computed**:
  - Velocity vectors ($\vec{v}_i$) per pedestrian.
  - Crowd flow direction vectors.
  - Turbulence index (detecting counter-flow movements that precede crowd collapse).

### 2.3 CSRNet (Dense Crowd Density Estimation)
- **Role**: Congested Scene Recognition Network designed specifically for extremely dense gatherings where individual bounding-box detection suffers severe occlusion.
- **Architecture**: VGG-16 front-end feature extractor combined with dilated convolutional back-end layers.
- **Output**: Continuous 2D crowd density distribution map, integrated to compute accurate total headcounts and local crowd density ($\text{ppl/m}^2$).

### 2.4 Risk Prediction & Early Warning Engine
- **Role**: Heuristic and probabilistic model calculating real-time safety risk score ($0.0$ to $1.0$).
- **Trigger Conditions**:
  - **Density Threshold**: $> 3.5 \text{ ppl/m}^2$ triggers a `WARNING`; $> 4.5 \text{ ppl/m}^2$ triggers `CRITICAL`.
  - **Bottleneck Accumulation**: Inflow rate significantly outpaces outflow rate at restricted exits.
  - **Turbulence / Panic Vector**: High variance in pedestrian direction vectors indicative of stampede dynamics.

---

## 3. Data Integration with Phase 1 Database

When active in Phase 2, the AI inference workers will persist telemetry directly to Supabase using the service role key:

```python
# Phase 2 Ingestion Contract
payload = {
    "camera_id": camera_uuid,
    "timestamp": datetime.utcnow().isoformat(),
    "people_count": detected_count,
    "density": calculated_density,
    "risk_score": current_risk_score,
    "status": "CRITICAL" if current_risk_score > 0.75 else "NORMAL"
}
supabase.table("crowd_logs").insert(payload).execute()
```
