import os
import logging
from typing import Dict, Any, Callable, Optional
from pathlib import Path
from .yolo_detector import YOLODetector

logger = logging.getLogger("crowdeye.ai.video_processor")


def process_video(
    video_path: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    frame_stride: int = 1,
    detector: Optional[YOLODetector] = None
) -> Dict[str, Any]:
    """
    Headless video processing engine for CrowdEye AI server environments.
    Strictly headless: does NOT call cv2.imshow() or require a GUI display.

    Args:
        video_path: Absolute or relative path to the input video file.
        progress_callback: Optional function(percent: int, current_count: int) to report progress.
        frame_stride: Process every N-th frame (default 1 = every frame).
        detector: Optional pre-loaded YOLODetector instance.

    Returns:
        {
            "total_frames": int,
            "average_people": int,
            "max_people": int,
            "duration": int  # in seconds
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
        fps = 25.0  # Fallback default FPS

    duration_sec = int(round(total_frames / fps)) if total_frames > 0 else 0

    logger.info(
        f"Starting headless video processing on '{path_obj.name}' "
        f"({total_frames} frames, {fps:.1f} FPS, {duration_sec}s duration)"
    )

    # 2. Instantiate YOLO detector
    if detector is None:
        detector = YOLODetector()

    frame_index = 0
    counts = []
    max_people = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Process frame based on stride
            if frame_index % frame_stride == 0:
                # 3 & 4. Run YOLO detection and count people
                detection_result = detector.detect_people(frame)
                current_count = detection_result.get("count", 0)
                counts.append(current_count)

                if current_count > max_people:
                    max_people = current_count

                # Update progress callback if provided
                if progress_callback and total_frames > 0:
                    percent = min(int((frame_index / total_frames) * 100), 99)
                    progress_callback(percent, current_count)

            frame_index += 1

    finally:
        cap.release()

    # 5 & 6. Aggregate results
    if counts:
        avg_people = int(round(sum(counts) / len(counts)))
    else:
        avg_people = 0

    # Final 100% progress callback
    if progress_callback:
        progress_callback(100, avg_people)

    logger.info(
        f"Video processing complete for '{path_obj.name}': "
        f"Total frames: {total_frames}, Avg: {avg_people}, Max: {max_people}, Duration: {duration_sec}s"
    )

    return {
        "total_frames": total_frames,
        "average_people": avg_people,
        "max_people": max_people,
        "duration": duration_sec
    }
