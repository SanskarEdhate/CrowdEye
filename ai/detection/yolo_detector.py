import os
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("crowdeye.ai.detector")


class YOLODetector:
    """
    YOLOv8 Person Detection Module for CrowdEye AI.
    Specialized strictly for human presence detection (COCO class ID 0).
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
        conf_threshold: float = 0.45,
        iou_threshold: float = 0.5,
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

            # Check if model is stored in models/ or project root
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

    def detect_people(self, frame) -> Dict[str, Any]:
        """
        Performs person detection on an input OpenCV BGR frame.

        Args:
            frame: numpy ndarray (BGR image from cv2.imread / cv2.VideoCapture)

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

        try:
            # Run inference with person class (0), conf (0.45), iou (0.5)
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
            logger.error(f"Error during YOLOv8 detection: {exc}")
            return {"count": 0, "persons": []}
