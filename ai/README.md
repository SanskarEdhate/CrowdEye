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

