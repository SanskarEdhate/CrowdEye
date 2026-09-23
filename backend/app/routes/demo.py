import os
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from app.services.camera_service import CameraService
from app.services.alert_service import AlertService
from app.websocket.tracking_socket import realtime_manager
from app.auth.auth import require_operator

logger = logging.getLogger("crowdeye.demo")

router = APIRouter(prefix="/demo", tags=["Demo Mode (Hackathon)"])

current_demo_scenario = "normal"


class DemoScenarioRequest(BaseModel):
    scenario: str = Field(..., description="Scenario type: 'low', 'medium', or 'critical'")
    camera_id: Optional[str] = None


@router.get("/status")
def get_demo_status():
    """
    TASK 11: Get current Demo Mode configuration and active scenario.
    """
    demo_mode = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
    return {
        "demo_mode": demo_mode,
        "active_scenario": current_demo_scenario,
        "available_scenarios": ["low", "medium", "critical"]
    }


@router.post("/scenario")
def set_demo_scenario(
    payload: DemoScenarioRequest,
    user: Dict[str, Any] = Depends(require_operator)
):
    """
    TASK 11 & TASK 15: Hackathon Interactive Scenario Controller.
    Transitions crowd conditions live during presentation:
    - 'low': Safe, low density, score 15, no alerts.
    - 'medium': Elevated, medium density, score 55, monitoring only.
    - 'critical': High bottleneck surge, density 4.5 ppl/m², score 92, triggers CRITICAL alert!
    """
    global current_demo_scenario
    scen = payload.scenario.lower()

    if scen not in ("low", "medium", "critical"):
        raise HTTPException(status_code=400, detail="Scenario must be 'low', 'medium', or 'critical'.")

    current_demo_scenario = scen
    cams = CameraService.get_cameras()
    target_cam_id = payload.camera_id or (cams[0]["id"] if cams else "cam-01")

    if scen == "low":
        for a in AlertService.get_alerts(status="ACTIVE"):
            AlertService.resolve_alert(str(a.get("id")), resolved_by="demo_safe_flow")
        CameraService.update_camera_telemetry(target_cam_id, people_count=90, density=0.8, risk_level="LOW")
        realtime_manager.sync_broadcast_risk(target_cam_id, {
            "type": "risk_update",
            "zone": "Zone A",
            "risk_score": 18.0,
            "risk_level": "LOW",
            "reasons": ["Normal crowd movement within safe thresholds"]
        })
        return {
            "scenario": "low",
            "message": "Demo scenario set to LOW CROWD (Safe, normal conditions).",
            "risk_score": 18.0,
            "risk_level": "LOW"
        }

    elif scen == "medium":
        CameraService.update_camera_telemetry(target_cam_id, people_count=450, density=2.2, risk_level="MEDIUM")
        realtime_manager.sync_broadcast_risk(target_cam_id, {
            "type": "risk_update",
            "zone": "Zone B",
            "risk_score": 52.0,
            "risk_level": "MEDIUM",
            "reasons": ["Elevated density in Concourse; monitoring only"]
        })
        return {
            "scenario": "medium",
            "message": "Demo scenario set to MEDIUM CROWD (Monitoring only, no alert).",
            "risk_score": 52.0,
            "risk_level": "MEDIUM"
        }

    elif scen == "critical":
        CameraService.update_camera_telemetry(target_cam_id, people_count=1380, density=4.6, risk_level="CRITICAL")
        
        # Trigger actual alert via AlertService (Task 4 & Task 11)
        alerts = AlertService.evaluate_and_create_alert(
            risk_input={
                "zone": "Zone C (Front Stage)",
                "risk_score": 92.5,
                "risk_level": "CRITICAL",
                "reasons": ["Critical surge threshold exceeded (>4.0 ppl/m²)", "Directional bottlenecking near Stage Area"]
            },
            camera_id=target_cam_id,
            camera_name="Stage Arena Cam 03"
        )

        realtime_manager.sync_broadcast_risk(target_cam_id, {
            "type": "risk_update",
            "zone": "Zone C",
            "risk_score": 92.5,
            "risk_level": "CRITICAL",
            "reasons": ["CRITICAL CROWD SURGE DETECTED (>4.0 ppl/m²)"]
        })

        return {
            "scenario": "critical",
            "message": "Demo scenario set to CRITICAL SURGE. High-risk safety alarm generated!",
            "risk_score": 92.5,
            "risk_level": "CRITICAL",
            "generated_alerts": alerts
        }
