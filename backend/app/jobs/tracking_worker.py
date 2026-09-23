import time
import logging
from pathlib import Path
from typing import Optional, Set, Dict, List
from datetime import datetime

logger = logging.getLogger("crowdeye.jobs.tracking_worker")


def run_tracking_worker(
    job_id: str,
    video_path: str,
    camera_id: Optional[str] = None
) -> None:
    """
    Background worker that runs YOLOv8 person detection + DeepSORT tracking,
    broadcasts real-time tracks over WebSockets, and writes 5-second movement
    summaries to Supabase.
    """
    import cv2
    import numpy as np
    from ai.detection.yolo_detector import YOLODetector
    from ai.tracking.deepsort_tracker import DeepSortTracker
    from ai.tracking.track_history import TrackHistory
    from ai.tracking.movement_analyzer import MovementAnalyzer
    from app.services.tracking_service import TrackingService
    from app.websocket.tracking_socket import tracking_manager

    logger.info(f"[Tracking Job {job_id}] Initializing tracking worker for: {video_path}")
    TrackingService.update_tracking_job(job_id, status="processing", progress=5)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.error(f"[Tracking Job {job_id}] Could not open video file: {video_path}")
        TrackingService.update_tracking_job(job_id, status="failed")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 25.0

    detector = YOLODetector()
    tracker = DeepSortTracker()
    history = TrackHistory(max_history_seconds=10.0)

    unique_person_ids: Set[int] = set()
    all_speeds: List[float] = []

    frame_interval_5sec = max(int(fps * 5), 1)
    frame_index = 0
    movement_buffer: List[Dict] = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            now_simulated = frame_index / fps  # Video time in seconds

            # 1. YOLOv8 Detection
            yolo_res = detector.detect_people(frame)
            persons = yolo_res.get("persons", [])

            # 2. DeepSORT Tracking
            tracks = tracker.update(persons, frame)

            frame_tracks_payload = []

            for track in tracks:
                pid = track["person_id"]
                unique_person_ids.add(pid)
                x1, y1, x2, y2 = track["bbox"]
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0

                # 3. Track History
                history.add_point(pid, cx, cy, timestamp=now_simulated)

                # 4. Movement Analysis
                recent_pts = history.get_recent_positions(pid, window_seconds=1.5)
                motion = MovementAnalyzer.analyze_motion(pid, recent_pts)
                direction = motion["direction"]
                speed = motion["speed"]
                all_speeds.append(speed)

                track_info = {
                    "person_id": pid,
                    "x": round(cx, 1),
                    "y": round(cy, 1),
                    "bbox": [x1, y1, x2, y2],
                    "direction": direction,
                    "speed": speed,
                    "unit": "pixels/sec"
                }
                frame_tracks_payload.append(track_info)

                # Buffer for 5-second Supabase write
                movement_buffer.append({
                    "person_id": pid,
                    "x_position": cx,
                    "y_position": cy,
                    "direction": direction,
                    "speed": speed,
                    "timestamp": datetime.utcnow().isoformat()
                })

            # Broadcast frame telemetry over WebSocket
            if frame_tracks_payload:
                ws_payload = {
                    "job_id": job_id,
                    "frame": frame_index,
                    "active_people": len(tracks),
                    "tracks": frame_tracks_payload
                }
                tracking_manager.sync_broadcast_track(job_id, ws_payload)

            # 5-second Periodic Batch Save to Supabase (Task 11)
            if frame_index > 0 and frame_index % frame_interval_5sec == 0:
                if movement_buffer:
                    TrackingService.batch_insert_movements(camera_id, movement_buffer)
                    movement_buffer.clear()

            # Progress update in Supabase
            if total_frames > 0 and frame_index % 10 == 0:
                progress = min(int((frame_index / total_frames) * 100), 98)
                TrackingService.update_tracking_job(
                    job_id,
                    progress=progress,
                    total_people=len(unique_person_ids)
                )

            frame_index += 1

        # Flush remaining movement buffer to Supabase
        if movement_buffer:
            TrackingService.batch_insert_movements(camera_id, movement_buffer)
            movement_buffer.clear()

        # Mark job as completed in Supabase
        avg_speed = round(sum(all_speeds) / len(all_speeds), 1) if all_speeds else 0.0
        TrackingService.update_tracking_job(
            job_id,
            status="completed",
            progress=100,
            total_people=len(unique_person_ids),
            completed=True
        )

        logger.info(
            f"[Tracking Job {job_id}] Successfully finished. "
            f"Unique People: {len(unique_person_ids)}, Avg Speed: {avg_speed} px/s"
        )

    except Exception as exc:
        logger.error(f"[Tracking Job {job_id}] Execution error: {exc}", exc_info=True)
        TrackingService.update_tracking_job(job_id, status="failed")

    finally:
        cap.release()
