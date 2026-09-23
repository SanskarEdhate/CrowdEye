import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.services.risk_service import RiskService
from app.websocket.tracking_socket import tracking_manager
from ai.risk.feature_extractor import FeatureExtractor
from ai.risk.risk_engine import RiskEngine
from ai.risk.risk_explainer import RiskExplainer
from ai.density.zone_manager import ZoneManager

logger = logging.getLogger("crowdeye.jobs.risk")


def run_risk_worker(job_id: str, camera_id: Optional[str] = None):
    """
    Background worker executing Phase 5 Risk Pipeline:
    1. Fetch last 10 seconds data from crowd_density & person_tracking
    2. Extract normalized features (Density, Speed, Chaos, Growth)
    3. Calculate deterministic explainable risk scores
    4. Generate human-readable justifications
    5. Save evaluations to Supabase crowd_risk
    6. Broadcast real-time early warnings over WebSockets
    7. Update risk_jobs status
    """
    logger.info(f"[RiskWorker] Starting risk evaluation job {job_id} (camera_id={camera_id})")
    RiskService.update_risk_job(job_id, status="processing", progress=20)

    try:
        # 1. Fetch 10-second temporal telemetry window
        telemetry = RiskService.fetch_recent_telemetry(camera_id=camera_id, window_seconds=10)
        density_recs = telemetry.get("density_records", [])
        movement_recs = telemetry.get("movement_records", [])

        RiskService.update_risk_job(job_id, progress=50)

        # 2. Setup zone mapping
        zone_mgr = ZoneManager()
        zone_capacities = {z.name: z.capacity for z in zone_mgr.zones}

        # Organize density by zone
        zone_density_map: Dict[str, List[Dict[str, Any]]] = {z.name: [] for z in zone_mgr.zones}
        for dr in density_recs:
            zn = dr.get("zone_name")
            if zn in zone_density_map:
                zone_density_map[zn].append(dr)

        # Organize movements by zone
        zone_movement_map: Dict[str, List[Dict[str, Any]]] = {z.name: [] for z in zone_mgr.zones}
        for mr in movement_recs:
            px = mr.get("x_position", 0.0)
            py = mr.get("y_position", 0.0)
            assigned_zone = zone_mgr.assign_to_zone(px, py)
            if assigned_zone and assigned_zone in zone_movement_map:
                zone_movement_map[assigned_zone].append(mr)

        evaluated_zones: List[Dict[str, Any]] = []
        db_records: List[Dict[str, Any]] = []
        iso_now = datetime.utcnow().isoformat()

        # 3. Evaluate each zone
        for zone in zone_mgr.zones:
            z_name = zone.name
            capacity = zone_capacities.get(z_name, 150)

            # Density & Growth estimation from records
            z_densities = zone_density_map.get(z_name, [])
            if z_densities:
                current_count = z_densities[0].get("people_count", 0)
                previous_count = z_densities[-1].get("people_count", current_count)
            else:
                # Fallback to movements count if density not logged yet
                current_count = len(zone_movement_map.get(z_name, []))
                previous_count = max(0, current_count - 1)

            # Speeds and Directions
            z_moves = zone_movement_map.get(z_name, [])
            if z_moves:
                speeds = [m.get("speed", 0.0) for m in z_moves]
                avg_speed = sum(speeds) / len(speeds)
                directions = [m.get("direction", "STATIONARY") for m in z_moves]
            else:
                avg_speed = 0.0
                directions = []

            # 4. Feature Extraction (Normalized 0 - 100)
            features = FeatureExtractor.extract_features(
                people_count=current_count,
                zone_capacity=capacity,
                previous_people=previous_count,
                current_speed=avg_speed,
                directions=directions
            )

            # 5. Risk Calculation (0.40*D + 0.25*S + 0.20*C + 0.15*G)
            risk_calc = RiskEngine.calculate_risk(
                density=features["density"],
                speed=features["speed"],
                chaos=features["chaos"],
                growth=features["growth"]
            )
            score = risk_calc["risk_score"]
            level = risk_calc["risk_level"]

            # 6. Human-readable explainability reasons
            reasons = RiskExplainer.explain_risk(score, features)

            zone_result = {
                "zone": z_name,
                "risk_score": score,
                "risk_level": level,
                "reason": reasons,
                "features": features
            }
            evaluated_zones.append(zone_result)

            db_records.append({
                "camera_id": camera_id,
                "zone_name": z_name,
                "risk_score": float(score),
                "risk_level": level,
                "risk_reason": reasons,
                "density_value": features["density"],
                "speed_value": features["speed"],
                "chaos_value": features["chaos"],
                "growth_value": features["growth"],
                "timestamp": iso_now
            })

            # Broadcast high-priority risk update over WebSocket if elevated
            if score >= 31:
                tracking_manager.sync_broadcast_risk(camera_id or "default", {
                    "type": "risk_update",
                    "camera_id": camera_id,
                    "zone": z_name,
                    "risk_score": score,
                    "risk_level": level,
                    "reasons": reasons
                })

        # 7. Persist to Supabase and cache result
        RiskService.insert_risk_records(db_records)
        RiskService.save_risk_result(camera_id or "default", evaluated_zones)

        RiskService.update_risk_job(
            job_id,
            status="completed",
            progress=100,
            completed_at=iso_now
        )
        logger.info(f"[RiskWorker] Successfully completed job {job_id}.")

    except Exception as exc:
        logger.exception(f"[RiskWorker] Job {job_id} failed: {exc}")
        RiskService.update_risk_job(job_id, status="failed")
