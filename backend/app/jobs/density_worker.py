import cv2
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.services.density_service import DensityService
from ai.detection.yolo_detector import YOLODetector
from ai.tracking.deepsort_tracker import DeepSortTracker
from ai.density.zone_manager import ZoneManager
from ai.density.perspective import PerspectiveTransformer
from ai.density.density_estimator import DensityEstimator
from ai.density.heatmap_generator import HeatmapGenerator
from ai.density.csrnet_optional import CSRNetVerifier

logger = logging.getLogger("crowdeye.jobs.density")


def run_density_worker(
    job_id: str,
    video_path: str,
    camera_id: Optional[str] = None
):
    """
    Background worker executing Phase 4 pipeline:
    Video -> YOLOv8 -> DeepSORT -> Perspective Correction -> Zone Mapping
          -> Density Estimation -> Dynamic Heatmap -> Optional CSRNet -> Supabase (5s Batches)
    """
    logger.info(f"[DensityWorker] Starting job {job_id} on video: {video_path}")
    DensityService.update_density_job(job_id, status="processing", progress=0)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"[DensityWorker] Cannot open video file: {video_path}")
        DensityService.update_density_job(job_id, status="failed", progress=0)
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

    # Initialize AI Components
    detector = YOLODetector()
    tracker = DeepSortTracker()
    zone_manager = ZoneManager(frame_width=width, frame_height=height)
    perspective_transformer = PerspectiveTransformer(frame_width=width, frame_height=height)
    density_estimator = DensityEstimator(zone_manager=zone_manager)
    heatmap_gen = HeatmapGenerator(grid_width=width, grid_height=height, downsample_factor=16)
    csrnet = CSRNetVerifier()

    frame_idx = 0
    last_db_flush = time.time()
    db_batch_records: List[Dict[str, Any]] = []

    latest_zones_summary: List[Dict[str, Any]] = []
    latest_heatmap_points: List[Dict[str, Any]] = []
    csrnet_verification_result: Optional[Dict[str, Any]] = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1

            # 1. YOLOv8 Detection
            det_result = detector.detect_people(frame)
            detections = det_result.get("persons", [])
            avg_conf = (
                sum(p.get("confidence", 0.0) for p in detections) / len(detections)
                if detections else 0.0
            )

            # 2. DeepSORT Tracking
            tracks = tracker.update(detections, frame)

            # 3. Person Centroids
            active_persons: List[Dict[str, Any]] = []
            for track in tracks:
                l, t, w, h = track["bbox"]
                cx = l + w / 2.0
                cy = t + h / 2.0
                active_persons.append({
                    "person_id": track["person_id"],
                    "x": cx,
                    "y": cy
                })

            # 4. Perspective Correction & Zone Density Estimation
            zone_densities = density_estimator.estimate_zone_densities(
                active_persons,
                perspective_transformer=perspective_transformer
            )
            latest_zones_summary = zone_densities

            # 5. Dynamic Heatmap Generation
            latest_heatmap_points = heatmap_gen.generate_heatmap_points(active_persons)

            # 6. Optional CSRNet Verification Trigger
            max_score = max((z["density_score"] for z in zone_densities), default=0.0)
            if csrnet.should_trigger(avg_conf, max_score) and csrnet_verification_result is None:
                # Trigger advisory CSRNet verification
                csrnet_verification_result = csrnet.verify_density(frame, len(active_persons))
                logger.info(f"[DensityWorker] CSRNet verification triggered: {csrnet_verification_result}")

            # 7. Batched Database Ingestion (Every 5 seconds)
            now_time = time.time()
            if now_time - last_db_flush >= 5.0:
                iso_now = datetime.utcnow().isoformat()
                for z in zone_densities:
                    db_batch_records.append({
                        "camera_id": camera_id,
                        "zone_name": z["zone"],
                        "people_count": z["people_count"],
                        "density_score": z["density_score"],
                        "density_level": z["density_level"],
                        "timestamp": iso_now
                    })

                DensityService.batch_insert_density_telemetry(db_batch_records)
                db_batch_records.clear()
                last_db_flush = now_time

            # Update progress periodically
            if total_frames > 0 and frame_idx % 10 == 0:
                progress = min(99, int((frame_idx / total_frames) * 100))
                DensityService.update_density_job(job_id, progress=progress)

        # Flush any remaining 5-second telemetry
        if db_batch_records:
            DensityService.batch_insert_density_telemetry(db_batch_records)
            db_batch_records.clear()

        # Save final formatted results
        DensityService.save_density_result(
            job_id=job_id,
            zones=latest_zones_summary,
            heatmap_points=latest_heatmap_points,
            csrnet_data=csrnet_verification_result
        )

        completed_at = datetime.utcnow().isoformat()
        DensityService.update_density_job(job_id, status="completed", progress=100, completed_at=completed_at)
        logger.info(f"[DensityWorker] Completed job {job_id} successfully.")

    except Exception as exc:
        logger.exception(f"[DensityWorker] Job {job_id} failed: {exc}")
        DensityService.update_density_job(job_id, status="failed")

    finally:
        cap.release()
