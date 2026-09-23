import time
import math
import logging
from typing import Dict, Any, List, Optional
import numpy as np

from ai_worker.config import (
    MODEL_NAME,
    DEVICE,
    CONF_THRESHOLD,
    IOU_THRESHOLD,
    ADAPTIVE_SAMPLE_NORMAL,
    ADAPTIVE_SAMPLE_HIGH_LOAD,
    HIGH_LOAD_LATENCY_THRESHOLD_MS,
    DEMO_MODE
)
from ai.detection.yolo_detector import YOLODetector
from ai.tracking.deepsort_tracker import DeepSortTracker
from ai.tracking.track_history import TrackHistory
from ai.tracking.movement_analyzer import MovementAnalyzer

logger = logging.getLogger("crowdeye.ai_worker.inference")


class UnifiedInferenceEngine:
    """
    Dedicated AI Inference Engine for the AI Worker service.
    Rules (TASK 1 & TASK 2):
    1. Loads YOLOv8n & DeepSORT models ONCE at startup.
    2. Adaptive frame sampling: throttles from 2nd frame to 5th frame under high load.
    3. Uses wall-clock timestamps for speed: distance / time_difference.
    4. Every detection record stores: timestamp, person_position, person_id.
    """

    _instance = None

    @classmethod
    def get_instance(cls) -> "UnifiedInferenceEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        logger.info(f"[InferenceEngine] Initializing models (device={DEVICE}, demo_mode={DEMO_MODE})...")
        t0 = time.time()

        # 1. Load YOLOv8 once at startup
        self.detector = YOLODetector.get_shared_instance(
            model_name=MODEL_NAME,
            conf_threshold=CONF_THRESHOLD,
            iou_threshold=IOU_THRESHOLD,
            device=DEVICE
        )

        # 2. Load DeepSORT tracker once at startup
        self.tracker = DeepSortTracker(max_age=30, n_init=2)

        # 3. Track History for wall-clock kinematics
        self.track_history = TrackHistory(max_history_seconds=10.0)

        # Moving average latency tracking for adaptive frame rate
        self.recent_latencies: List[float] = []
        self.last_latency_ms: float = 20.0
        self.total_frames_processed: int = 0

        load_sec = round(time.time() - t0, 2)
        logger.info(f"[InferenceEngine] All models initialized successfully in {load_sec}s.")

    def get_adaptive_step(self) -> int:
        """
        TASK 2: Adaptive frame sampling.
        High load (>80ms per frame): Process every 5th frame.
        Normal load (<=80ms): Process every 2nd frame.
        """
        if self.last_latency_ms > HIGH_LOAD_LATENCY_THRESHOLD_MS:
            return ADAPTIVE_SAMPLE_HIGH_LOAD
        return ADAPTIVE_SAMPLE_NORMAL

    def process_frame(
        self,
        frame: np.ndarray,
        wall_clock_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Processes a single video frame through detection, tracking, and kinematics.
        Uses wall-clock timestamps.
        """
        start_t = time.time()
        now_ts = wall_clock_time if wall_clock_time is not None else start_t

        # 1. Run YOLOv8 Person Detection
        det_result = self.detector.detect_people(frame)
        raw_detections = det_result.get("persons", [])

        # 2. Run DeepSORT Tracking
        tracking_result = self.tracker.update(raw_detections, frame)
        active_tracks = tracking_result if isinstance(tracking_result, list) else tracking_result.get("tracks", [])

        detections_with_meta: List[Dict[str, Any]] = []

        # 3. Update spatial-temporal history & calculate kinematics using wall-clock time
        for trk in active_tracks:
            pid = trk["person_id"]
            bbox = trk.get("bbox") or [trk.get("x1", 0), trk.get("y1", 0), trk.get("x2", 0), trk.get("y2", 0)]
            x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
            px = trk.get("x", int((x1 + x2) / 2))
            py = trk.get("y", int((y1 + y2) / 2))

            # Store detection record (TASK 1 format)
            det_record = self.track_history.add_point(pid, px, py, timestamp=now_ts)

            # Kinematics analysis over wall-clock window
            recent_pts = self.track_history.get_recent_positions(pid, window_seconds=2.0)
            motion = MovementAnalyzer.analyze_motion(pid, recent_pts)

            det_record.update({
                "direction": motion["direction"],
                "speed": motion["speed"],
                "bbox": [x1, y1, x2, y2],
                "confidence": trk.get("confidence", 0.9)
            })
            detections_with_meta.append(det_record)

        self.track_history.prune_stale_tracks(max_idle_seconds=15.0, current_time=now_ts)

        # 4. Measure wall-clock inference latency
        elapsed_ms = (time.time() - start_t) * 1000.0
        self.last_latency_ms = elapsed_ms
        self.recent_latencies.append(elapsed_ms)
        if len(self.recent_latencies) > 50:
            self.recent_latencies.pop(0)

        self.total_frames_processed += 1
        adaptive_step = self.get_adaptive_step()

        return {
            "timestamp": now_ts,
            "people_count": len(detections_with_meta),
            "detections": detections_with_meta,
            "latency_ms": round(elapsed_ms, 2),
            "adaptive_step": adaptive_step,
            "fps": round(1000.0 / max(elapsed_ms, 1.0), 1)
        }
