import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger("crowdeye.ai.detector")


def _apply_nms(boxes: List[List[float]], scores: List[float], iou_threshold: float = 0.45) -> List[int]:
    """
    Applies Non-Maximum Suppression to remove duplicate bounding boxes.
    Uses torchvision if available, with robust NumPy fallback.
    """
    if not boxes:
        return []

    try:
        import torch
        import torchvision
        boxes_t = torch.tensor(boxes, dtype=torch.float32)
        scores_t = torch.tensor(scores, dtype=torch.float32)
        keep = torchvision.ops.nms(boxes_t, scores_t, iou_threshold=iou_threshold)
        return keep.tolist()
    except Exception:
        boxes_np = np.array(boxes, dtype=np.float32)
        scores_np = np.array(scores, dtype=np.float32)
        x1 = boxes_np[:, 0]
        y1 = boxes_np[:, 1]
        x2 = boxes_np[:, 2]
        y2 = boxes_np[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores_np.argsort()[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(int(i))
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
            inds = np.where(ovr <= iou_threshold)[0]
            order = order[inds + 1]
        return keep


class YOLODetector:
    """
    YOLOv8 Person Detection Module for CrowdEye AI.
    Specialized for human presence detection (COCO class ID 0) with support for
    dense crowd surveillance footage, wide aspect ratio cameras, and multi-scale tiling.
    """

    PERSON_CLASS_ID = 0  # COCO class 0 is 'person'
    _shared_instance = None

    @classmethod
    def get_shared_instance(cls, **kwargs) -> "YOLODetector":
        """
        TASK 2: Load model once at application startup.
        Do NOT load model per request.
        """
        if cls._shared_instance is None or cls._shared_instance.model is None:
            cls._shared_instance = cls(**kwargs)
        else:
            if "conf_threshold" in kwargs:
                cls._shared_instance.conf_threshold = kwargs["conf_threshold"]
            if "iou_threshold" in kwargs:
                cls._shared_instance.iou_threshold = kwargs["iou_threshold"]
        return cls._shared_instance

    @classmethod
    def load_model_once(cls, **kwargs) -> "YOLODetector":
        """Explicit startup pre-warm hook."""
        return cls.get_shared_instance(**kwargs)

    @staticmethod
    def get_adaptive_frame_step(last_latency_ms: float) -> int:
        """
        TASK 2: Adaptive frame processing rule:
        High load (>80ms per frame): Process every 5th frame
        Normal load (<=80ms): Process every 2nd frame
        """
        if last_latency_ms > 80.0:
            return 5
        return 2

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        conf_threshold: float = 0.20,
        iou_threshold: float = 0.45,
        device: str = "cpu"
    ):
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.model = None
        self.load_model()

    def load_model(self) -> None:
        """
        Loads the YOLOv8 model weights using Ultralytics.
        Automatically downloads yolov8n.pt if not found locally.
        """
        try:
            from ultralytics import YOLO

            models_dir = Path(__file__).resolve().parent.parent / "models"
            model_path = models_dir / self.model_name

            if model_path.exists():
                logger.info(f"Loading YOLOv8 from local models directory: {model_path}")
                self.model = YOLO(str(model_path))
            else:
                logger.info(f"Loading YOLOv8 model: {self.model_name}")
                self.model = YOLO(self.model_name)

            logger.info("YOLOv8 model loaded successfully.")
        except ImportError:
            logger.error("Ultralytics package not installed. Run 'pip install ultralytics'.")
            self.model = None
        except Exception as exc:
            logger.error(f"Failed to load YOLOv8 model: {exc}")
            self.model = None

    def detect_people(self, frame, crowd_mode: bool = True) -> Dict[str, Any]:
        """
        Performs person detection on an input OpenCV BGR frame.
        Supports dense crowd detection via multi-tile inference for wide/panoramic footage.

        Args:
            frame: numpy ndarray (BGR image from cv2.imread / cv2.VideoCapture)
            crowd_mode: whether to enable multi-tile dense crowd detection on high-res frames.

        Returns:
            {
                "count": int,
                "persons": [
                    {
                        "x1": int,
                        "y1": int,
                        "x2": int,
                        "y2": int,
                        "confidence": float
                    }
                ]
            }
        """
        if self.model is None:
            self.load_model()
            if self.model is None:
                logger.warning("YOLOv8 model unavailable. Returning 0 detections.")
                return {"count": 0, "persons": []}

        h, w = frame.shape[:2]

        try:
            # Multi-tile dense crowd processing for wide/HD cameras (>1200px width)
            if crowd_mode and w > 1200:
                slice_w = int(w * 0.58)
                left_tile = frame[:, :slice_w]
                right_tile = frame[:, w - slice_w:]

                res_left = self.model.predict(
                    source=left_tile,
                    classes=[self.PERSON_CLASS_ID],
                    conf=self.conf_threshold,
                    imgsz=960,
                    verbose=False,
                    device=self.device
                )[0]

                res_right = self.model.predict(
                    source=right_tile,
                    classes=[self.PERSON_CLASS_ID],
                    conf=self.conf_threshold,
                    imgsz=960,
                    verbose=False,
                    device=self.device
                )[0]

                raw_boxes = []
                raw_scores = []

                # Collect left tile boxes
                for b in res_left.boxes:
                    coords = b.xyxy[0].tolist()
                    conf = float(b.conf[0].item() if hasattr(b.conf, "__len__") else b.conf.item())
                    raw_boxes.append(coords)
                    raw_scores.append(conf)

                # Collect right tile boxes (offset x coordinates)
                offset_x = w - slice_w
                for b in res_right.boxes:
                    coords = b.xyxy[0].tolist()
                    coords[0] += offset_x
                    coords[2] += offset_x
                    conf = float(b.conf[0].item() if hasattr(b.conf, "__len__") else b.conf.item())
                    raw_boxes.append(coords)
                    raw_scores.append(conf)

                if not raw_boxes:
                    return {"count": 0, "persons": []}

                keep_indices = _apply_nms(raw_boxes, raw_scores, iou_threshold=self.iou_threshold)

                persons = []
                for idx in keep_indices:
                    box = raw_boxes[idx]
                    conf = raw_scores[idx]
                    persons.append({
                        "x1": int(round(box[0])),
                        "y1": int(round(box[1])),
                        "x2": int(round(box[2])),
                        "y2": int(round(box[3])),
                        "confidence": round(conf, 3)
                    })

                return {
                    "count": len(persons),
                    "persons": persons
                }

            # Standard detection for smaller frames
            results = self.model.predict(
                source=frame,
                classes=[self.PERSON_CLASS_ID],
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=False,
                device=self.device
            )

            persons: List[Dict[str, Any]] = []

            if results and len(results) > 0:
                boxes = results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0].item()) if hasattr(box.cls, "__len__") else int(box.cls.item())
                    if cls_id == self.PERSON_CLASS_ID:
                        coords = box.xyxy[0].tolist()
                        conf = float(box.conf[0].item() if hasattr(box.conf, "__len__") else box.conf.item())

                        persons.append({
                            "x1": int(round(coords[0])),
                            "y1": int(round(coords[1])),
                            "x2": int(round(coords[2])),
                            "y2": int(round(coords[3])),
                            "confidence": round(conf, 3)
                        })

            return {
                "count": len(persons),
                "persons": persons
            }

        except Exception as exc:
            logger.error(f"Error during YOLOv8 detection: {exc}", exc_info=True)
            return {"count": 0, "persons": []}
