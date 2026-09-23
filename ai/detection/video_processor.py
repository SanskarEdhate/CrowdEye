import os
import logging
from typing import Dict, Any, Callable, Optional, List
from pathlib import Path
from .yolo_detector import YOLODetector

logger = logging.getLogger("crowdeye.ai.video_processor")


def process_video(
    video_path: str,
    progress_callback: Optional[Callable[..., None]] = None,
    frame_stride: Optional[int] = None,
    detector: Optional[YOLODetector] = None
) -> Dict[str, Any]:
    """
    Headless video processing engine for CrowdEye AI server environments.
    Extracts frame-by-frame person counts, peak density, and keyframe bounding boxes.

    Args:
        video_path: Absolute or relative path to the input video file.
        progress_callback: Optional callback(percent: int, current_count: int, frame_idx: int, total_frames: int, boxes: list)
        frame_stride: Process every N-th frame (if None, adaptively selects stride based on video length).
        detector: Optional pre-loaded YOLODetector instance.

    Returns:
        {
            "total_frames": int,
            "average_people": int,
            "max_people": int,
            "duration": int,
            "sample_frames": List[Dict[str, Any]],
            "initial_boxes": List[Dict[str, Any]]
        }
    """
    import cv2

    path_obj = Path(video_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    # 1. Open video using OpenCV
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video stream from {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 25.0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080

    duration_sec = int(round(total_frames / fps)) if total_frames > 0 else 0

    # Adaptive stride: ensure dense crowd inference completes in 10-15s
    if frame_stride is None:
        if total_frames > 400:
            frame_stride = max(6, int(total_frames / 40))
        elif total_frames > 150:
            frame_stride = 6
        else:
            frame_stride = 2

    logger.info(
        f"Starting headless video processing on '{path_obj.name}' "
        f"({total_frames} frames, {width}x{height}, {fps:.1f} FPS, stride={frame_stride})"
    )

    # 2. Instantiate YOLO detector with optimized threshold for dense crowds
    if detector is None:
        detector = YOLODetector.get_shared_instance(conf_threshold=0.20)

    frame_index = 0
    counts: List[int] = []
    max_people = 0
    sample_frames: List[Dict[str, Any]] = []
    initial_boxes: List[Dict[str, Any]] = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Process frame based on stride
            if frame_index % frame_stride == 0:
                detection_result = detector.detect_people(frame)
                current_count = detection_result.get("count", 0)
                counts.append(current_count)

                if current_count > max_people:
                    max_people = current_count

                # Normalize bounding boxes to [0, 1] relative coordinates for web player
                norm_boxes = []
                for p in detection_result.get("persons", []):
                    bx1 = max(0, p.get("x1", 0))
                    by1 = max(0, p.get("y1", 0))
                    bx2 = min(width, p.get("x2", 0))
                    by2 = min(height, p.get("y2", 0))
                    bw = max(0, bx2 - bx1)
                    bh = max(0, by2 - by1)

                    if bw > 0 and bh > 0:
                        norm_boxes.append({
                            "x": round(bx1 / width, 4),
                            "y": round(by1 / height, 4),
                            "w": round(bw / width, 4),
                            "h": round(bh / height, 4),
                            "confidence": round(float(p.get("confidence", 0.85)), 2)
                        })

                if not initial_boxes and norm_boxes:
                    initial_boxes = norm_boxes

                # Keep sampled keyframes (up to 80 frames max to keep payload light)
                if len(sample_frames) < 80:
                    sample_frames.append({
                        "frame": frame_index,
                        "time": round(frame_index / fps, 2),
                        "count": current_count,
                        "boxes": norm_boxes
                    })

                # Report progress
                if progress_callback and total_frames > 0:
                    percent = min(int((frame_index / total_frames) * 100), 99)
                    try:
                        progress_callback(percent, current_count, frame_index, total_frames, norm_boxes)
                    except TypeError:
                        progress_callback(percent, current_count)

            frame_index += 1

    finally:
        cap.release()

    # Aggregate results
    avg_people = int(round(sum(counts) / len(counts))) if counts else 0

    if progress_callback:
        try:
            progress_callback(100, avg_people, total_frames, total_frames, initial_boxes)
        except TypeError:
            progress_callback(100, avg_people)

    logger.info(
        f"Video processing complete for '{path_obj.name}': "
        f"Frames: {total_frames}, Avg: {avg_people}, Peak: {max_people}, Duration: {duration_sec}s"
    )

    return {
        "total_frames": total_frames,
        "average_people": avg_people,
        "max_people": max_people,
        "duration": duration_sec,
        "sample_frames": sample_frames,
        "initial_boxes": initial_boxes
    }
