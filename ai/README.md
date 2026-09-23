# CrowdEye AI - Artificial Intelligence Module Specification

> **Phase 2 Implementation: YOLOv8 Person Detection & Video Ingestion**

This directory houses the computer vision detection pipeline for CrowdEye AI.

---

## 1. Phase 2 Scope & Overview

In Phase 2, the primary computer vision foundation is established:
- **Model**: YOLOv8 Nano (`yolov8n.pt`)
- **Target Class**: Person (COCO Class ID: `0`)
- **Confidence Threshold**: $\ge 0.45$
- **IoU Threshold**: $\ge 0.5$
- **Inference Mode**: Headless batch frame processing via OpenCV (`cv2.VideoCapture`)
- **Storage Strategy**: Final aggregated headcount stored directly in Supabase `crowd_logs` with `status: "DETECTED"`.

*Future modules (DeepSORT tracking, CSRNet density heatmaps, risk prediction, alerts) remain reserved for Phase 3+.*

---

## 2. Directory Architecture

```
ai/
├── detection/
│   ├── __init__.py           # Package exports (YOLODetector, process_video)
│   ├── yolo_detector.py      # Core YOLOv8 inference class
│   ├── video_processor.py    # Headless server-safe OpenCV processing pipeline
│   └── demo_viewer.py        # Local developer utility with cv2.imshow()
├── models/
│   └── README.md             # Weights documentation (*.pt ignored by git)
└── README.md
```

---

## 3. YOLOv8 Detection Pipeline

```
  [ Video / CCTV Recording (.mp4) ]
                 |
                 v
     [ cv2.VideoCapture ]
                 |
                 v
    [ Frame Extraction Loop ]
                 |
                 v
   [ YOLODetector.detect_people() ]
     - Filter: class_id == 0 (person)
     - Filter: conf >= 0.45, iou = 0.5
                 |
                 v
     [ Person Count Extraction ]
                 |
                 v
     [ Aggregate Computation ]
     - Total Frames
     - Average People
     - Peak People (Max Count)
     - Duration (seconds)
                 |
                 v
    [ Supabase crowd_logs Insert ]
     - people_count: <calculated count>
     - density: NULL
     - risk_score: NULL
     - status: "DETECTED"
```

---

## 4. Component Details

### 4.1 `yolo_detector.py`
Defines `YOLODetector`:
- Automatically downloads and caches `yolov8n.pt` on first use via Ultralytics.
- `detect_people(frame)` takes a BGR image array and returns:
  ```json
  {
    "count": 25,
    "persons": [
      {
        "x1": 100,
        "y1": 50,
        "x2": 200,
        "y2": 250,
        "confidence": 0.91
      }
    ]
  }
  ```

### 4.2 `video_processor.py`
Defines `process_video(video_path, progress_callback, frame_stride)`:
- Server-safe headless engine. **Never calls `cv2.imshow()`**.
- Supports optional `progress_callback(percent, count)` used by the FastAPI background worker to report progress back to the user interface.
- Returns:
  ```json
  {
    "total_frames": 3000,
    "average_people": 250,
    "max_people": 400,
    "duration": 120
  }
  ```

### 4.3 `demo_viewer.py`
Developer-only local testing script:
- Runs live video with bounding boxes, headcount banner, and FPS overlay using `cv2.imshow()`.
- Run locally with:
  ```bash
  python ai/detection/demo_viewer.py videos/input/test.mp4
  ```

---

## 5. Testing Steps (Phase 2)

1. **Verify Weights & Package**:
   ```bash
   python -c "from ai.detection.yolo_detector import YOLODetector; d = YOLODetector(); print('YOLOv8 initialized OK!')"
   ```
2. **Process Sample Video Headless**:
   ```bash
   python -c "from ai.detection.video_processor import process_video; print(process_video('videos/input/test.mp4'))"
   ```
3. **Run Interactive Demo Viewer (Optional GUI)**:
   ```bash
   python ai/detection/demo_viewer.py videos/input/test.mp4
   ```

---

## 6. Phase 3: DeepSORT Person Tracking + Movement Analysis

Phase 3 upgrades the system from answering *"How many people are present?"* to *"How are people moving inside the crowd?"*

### 6.1 Tracking Architecture

```
ai/
├── tracking/
│   ├── __init__.py           # Exports Tracker, TrackHistory, MovementAnalyzer
│   ├── deepsort_tracker.py   # Appearance-based DeepSORT tracker (MobileNet)
│   ├── track_history.py      # Rolling coordinate buffer (10s window)
│   └── movement_analyzer.py  # 8-way directional heading + velocity (px/s)
└── visualization/
    ├── __init__.py
    └── tracking_viewer.py    # Local GUI viewer with trajectories & vectors
```

### 6.2 Key Parameters & Algorithms

- **Embedder**: `MobileNet` via `deep-sort-realtime`. Extracts visual appearance feature vectors to persist unique person IDs through occlusions.
- **Track Lifecycle**:
  - `max_age = 30`: Tracks survive up to 30 consecutive missed detections before termination.
  - `n_init = 2`: Tracks require 2 consecutive detections to graduate to `CONFIRMED`.
  - `max_iou_distance = 0.7`: Kalman filter spatial gating distance.
- **Direction Calculation**:
  - Computes $\theta = \operatorname{atan2}(-\Delta y, \Delta x)$ over the last 10 frames.
  - Classified into 8 cardinal compass directions: `UP`, `DOWN`, `LEFT`, `RIGHT`, `UP-LEFT`, `UP-RIGHT`, `DOWN-LEFT`, `DOWN-RIGHT`, or `STATIONARY` if movement $\le 5$ pixels.
- **Relative Speed**:
  - Strictly measured in **`pixels/sec`**:
    $$\text{speed} = \frac{\sqrt{\Delta x^2 + \Delta y^2}}{\Delta t}$$
  - No meters/second conversion is performed, avoiding inaccuracies due to lack of camera calibration.
- **Track History Window**:
  - Stores `(x, y, timestamp)` tuples up to 10 seconds into a rolling `deque`.

### 6.3 Local Visualizer Testing

Run the local GUI tracking visualizer on any video:
```bash
python ai/visualization/tracking_viewer.py videos/input/crowd_tracking.mp4
```
Press `q` to exit. Displays confirmed IDs, bounding boxes, centroid dots, green trajectory trails, and heading arrows.

---

## 7. Phase 4: Crowd Density Estimation + Zone Heatmap System

Phase 4 elevates crowd monitoring from *"How many people are present?"* to *"Where is the crowd concentrated and how crowded is each zone?"*

### 7.1 Architecture Overview

```
ai/
├── density/
│   ├── __init__.py           # Exports ZoneManager, Perspective, Estimator, Heatmap, CSRNet
│   ├── zone_manager.py       # Spatial partition grid (Zones A-F) & point-in-polygon mapping
│   ├── perspective.py        # OpenCV homography perspective distortion rectification
│   ├── density_estimator.py  # 4-tier normalized density score calculation
│   ├── heatmap_generator.py  # Dynamic 2D Gaussian density cloud data generation
│   └── csrnet_optional.py    # Conditional dilated CSRNet verification model
```

### 7.2 Density Calculation & Zone Capacity
- **Zone Partitioning**: The camera view is partitioned into a nominal 2×3 grid:
  - Zones A, B, C (top/distant tier)
  - Zones D, E, F (bottom/foreground tier)
- **Formula**:
  $$\text{Density Score} = \frac{\text{people\_count}}{\text{zone\_capacity}}$$
- **4-Tier Classification**:
  - `LOW`: $0\% \le \text{score} < 40\%$
  - `MEDIUM`: $40\% \le \text{score} < 70\%$
  - `HIGH`: $70\% \le \text{score} < 90\%$
  - `CRITICAL`: $\text{score} \ge 90\%$

### 7.3 Camera Perspective Calibration Note
- **Projective Homography**: Camera tilt introduces non-linear ground plane foreshortening where distant people appear smaller and packed tighter in image pixels.
- `ai/density/perspective.py` applies OpenCV 2D homography ($3 \times 3$ transformation matrix):
  $$\begin{bmatrix} x' \\ y' \\ 1 \end{bmatrix} \sim \mathbf{H} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}$$
- **Important**: Accurate physical density (people / $\text{m}^2$) requires physical camera calibration (focal length, elevation angle, ground markers). A calibrated default trapezoid rectification is applied out of the box.

### 7.4 Dynamic Heatmap Generation
- **Strategy**: **Never save raw image files continuously to disk or database.**
- `HeatmapGenerator` applies 2D Gaussian kernels to person centroids:
  $$G(x, y) = \exp\left(-\frac{(x - x_0)^2 + (y - y_0)^2}{2\sigma^2}\right)$$
- Downsamples matrix to an array of coordinate-intensity points:
  ```json
  [
    { "x": 250, "y": 400, "intensity": 0.82 }
  ]
  ```
- Rendered client-side on HTML5 Canvas via radial gradients.

### 7.5 Optional CSRNet Verification Module & Limitations
- **Architecture**: VGG-16 frontend (10 layers) + Dilated Conv backend (dilation rate 2) preserving spatial resolution without pooling artifacts.
- **Strict Invocation Guard**:
  - Only triggered when average YOLO confidence drops ($< 0.50$) OR any zone density score exceeds $0.70$.
  - **NEVER** runs on every frame.
  - **NEVER** directly replaces or blindly averages with YOLO count.
  - Outputs advisory confirmation: `{"estimated_count": int, "confidence": "experimental"}`.
- **Pretrained Checkpoint Reference**: Trained on ShanghaiTech Part A (dense) and Part B (moderate) crowd counting benchmarks (`ai/models/csrnet_shanghaitech.pth`).

---

## 8. Phase 5: Crowd Risk Prediction + Early Warning Engine

Phase 5 introduces deterministic, explainable safety risk modeling over rolling 10-second temporal telemetry windows.

### 8.1 Architecture Overview

```
ai/
├── risk/
│   ├── __init__.py           # Exports FeatureExtractor, RiskEngine, RiskExplainer, BaseRiskModel
│   ├── feature_extractor.py  # 10s temporal window normalization (Density, Growth, Speed, Chaos)
│   ├── risk_engine.py        # Deterministic weighted formula & 4-tier level classification
│   ├── risk_explainer.py     # Diagnostic human-readable safety justifications
│   └── risk_model.py         # Extensible BaseRiskModel interface for future ML algorithms
```

### 8.2 Deterministic Risk Formula & Feature Normalization
Every feature is strictly normalized into a uniform $[0.0, 100.0]$ domain:
1. **Density ($D$)**:
   $$\text{density\_norm} = \min\left(100.0, \; \frac{\text{people\_count}}{\text{zone\_capacity}} \times 100\right)$$
2. **Growth Rate ($G$)**:
   $$\text{growth\_rate} = \frac{\text{current\_people} - \text{previous\_people}}{\max(1, \text{previous\_people})} \times 100, \quad \text{growth\_norm} = \max(0.0, \min(100.0, \text{growth\_rate}))$$
3. **Movement Speed ($S$)**:
   $$\text{speed\_norm} = \min\left(100.0, \; \frac{\text{current\_speed}}{\text{max\_expected\_speed}} \times 100\right) \quad (\text{where } \text{max\_expected\_speed} = 150.0\text{ px/s})$$
4. **Movement Chaos ($C$) using Circular Statistics**:
   Standard linear variance $\text{Var}(\theta)$ is flawed for angular data because $0 \equiv 2\pi$. Circular statistics resolves this via the mean resultant vector length $R$:
   $$C_x = \sum_{i=1}^n \cos \theta_i, \quad S_y = \sum_{i=1}^n \sin \theta_i, \quad R = \frac{\sqrt{C_x^2 + S_y^2}}{n}$$
   $$\text{chaos\_norm} = (1.0 - R) \times 100$$
   *(Pure unidirectional crowd yields $R = 1.0 \implies \text{Chaos} = 0\%$; opposing counter-flow yields $R = 0.0 \implies \text{Chaos} = 100\%$)*.

### 8.3 Composite Risk Formula
$$\text{Risk Score} = 0.40 \times D + 0.25 \times S + 0.20 \times C + 0.15 \times G$$

### 8.4 4-Tier Safety Levels
- `0 - 30`: **`LOW`** (Routine venue conditions; normal flow)
- `31 - 60`: **`MEDIUM`** (Moderate accumulation or growth; monitor corridors)
- `61 - 80`: **`HIGH`** (Dangerous congestion forming; dispatch marshals)
- `81 - 100`: **`CRITICAL`** (Imminent crowd crush / severe bottleneck early warning)

### 8.5 Risk Prediction Limitations
- **Early Warning Only**: The model assesses *potential crowd safety risk*; it does not claim to detect accidents or stampedes in progress.
- **Explainability**: Calculation is 100% deterministic and transparent, avoiding uninterpretable black-box ML outputs.
- **Future ML Expansion**: `ai/risk/risk_model.py` provides abstract `BaseRiskModel.predict(features)` ready for future Random Forest, XGBoost, or LSTM models.



