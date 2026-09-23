import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger("crowdeye.ai.deepsort")


class DeepSortTracker:
    """
    Appearance-based DeepSORT Multi-Object Tracker for CrowdEye AI.
    Uses MobileNet embeddings to preserve person identity through occlusion.
    """

    def __init__(
        self,
        max_age: int = 30,
        n_init: int = 3,
        max_iou_distance: float = 0.7,
        embedder: str = "mobilenet"
    ):
        self.max_age = max_age
        self.n_init = n_init
        self.max_iou_distance = max_iou_distance
        self.embedder = embedder
        self.tracker = None
        self._initialize_tracker()

    def _initialize_tracker(self):
        """
        Initializes the deep_sort_realtime DeepSort tracker instance.
        """
        try:
            from deep_sort_realtime.deepsort_tracker import DeepSort

            self.tracker = DeepSort(
                max_age=self.max_age,
                n_init=self.n_init,
                max_iou_distance=self.max_iou_distance,
                embedder=self.embedder
            )
            logger.info(
                f"DeepSORT initialized successfully with embedder='{self.embedder}', "
                f"max_age={self.max_age}, n_init={self.n_init}, max_iou={self.max_iou_distance}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize DeepSORT: {e}")
            self.tracker = None

    def update(self, arg1, arg2=None) -> List[Dict[str, Any]]:
        """
        Updates tracking state using current frame detections and image appearance features.
        Accepts either update(yolo_persons, frame) or update(frame, yolo_persons).

        Returns:
            [
                {
                    "person_id": int,
                    "bbox": [x1, y1, x2, y2],
                    "confidence": float
                }
            ]
        """
        if isinstance(arg1, np.ndarray):
            frame = arg1
            yolo_persons = arg2 if arg2 is not None else []
        elif isinstance(arg2, np.ndarray):
            frame = arg2
            yolo_persons = arg1 if arg1 is not None else []
        else:
            yolo_persons = arg1 if isinstance(arg1, list) else []
            frame = arg2
        if self.tracker is None:
            self._initialize_tracker()
            if self.tracker is None:
                return []

        # Convert YOLO [x1, y1, x2, y2] to DeepSort format: ([left, top, width, height], confidence, class)
        raw_detections = []
        for p in yolo_persons:
            if isinstance(p, dict):
                x1, y1, x2, y2 = p["x1"], p["y1"], p["x2"], p["y2"]
                conf = float(p.get("confidence", 0.9))
            elif isinstance(p, (list, tuple, np.ndarray)):
                x1, y1, x2, y2 = float(p[0]), float(p[1]), float(p[2]), float(p[3])
                conf = float(p[4]) if len(p) > 4 else 0.9
            else:
                continue
            w = max(x2 - x1, 1)
            h = max(y2 - y1, 1)
            raw_detections.append(([x1, y1, w, h], conf, "person"))

        # Run DeepSORT tracking step
        try:
            tracks = self.tracker.update_tracks(raw_detections, frame=frame)
        except Exception as exc:
            logger.error(f"Error during DeepSORT update_tracks: {exc}")
            return []

        active_tracks: List[Dict[str, Any]] = []

        for track in tracks:
            # Check if track is confirmed by Kalman filter
            if not track.is_confirmed():
                continue

            track_id_str = track.track_id
            try:
                person_id = int(track_id_str)
            except ValueError:
                # Handle non-integer ID if any
                person_id = abs(hash(track_id_str)) % 100000

            # Convert to [x1, y1, x2, y2]
            ltrb = track.to_ltrb()
            x1 = int(round(ltrb[0]))
            y1 = int(round(ltrb[1]))
            x2 = int(round(ltrb[2]))
            y2 = int(round(ltrb[3]))

            conf = track.get_det_conf()
            if conf is None:
                conf = 0.90

            active_tracks.append({
                "person_id": person_id,
                "bbox": [x1, y1, x2, y2],
                "confidence": round(float(conf), 3)
            })

        return active_tracks
