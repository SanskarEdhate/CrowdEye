from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.services.camera_service import CameraService
from app.auth.security import require_admin, require_operator

router = APIRouter(tags=["Camera Management"])


class CameraCreateRequest(BaseModel):
    camera_name: str = Field(..., description="Camera identifier name, e.g. North Gate Cam 01")
    zone: str = Field(default="Zone A", description="Designated zone or sector")
    location: Optional[str] = Field(default="Main Arena", description="Physical location")
    stream_url: Optional[str] = Field(default="", description="RTSP / HLS stream URL")
    status: Optional[str] = Field(default="ACTIVE", description="Camera operating status: ACTIVE, MAINTENANCE, OFFLINE")
    zone_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Zone homography & grid config")
    event_id: Optional[str] = Field(default=None, description="Associated public event UUID")


class CameraUpdateRequest(BaseModel):
    camera_name: Optional[str] = None
    zone: Optional[str] = None
    location: Optional[str] = None
    stream_url: Optional[str] = None
    status: Optional[str] = None
    zone_config: Optional[Dict[str, Any]] = None


@router.post("/cameras", response_model=Dict[str, Any], status_code=201)
@router.post("/api/v1/cameras", response_model=Dict[str, Any], status_code=201)
def create_camera(
    payload: CameraCreateRequest,
    user: Dict[str, Any] = Depends(require_admin)
):
    """
    TASK 7: Create a new camera.
    ADMIN ONLY. OPERATORS receive HTTP 403 Forbidden.
    """
    created = CameraService.create_camera(
        camera_name=payload.camera_name,
        zone=payload.zone,
        location=payload.location,
        stream_url=payload.stream_url,
        status=payload.status or "ACTIVE",
        zone_config=payload.zone_config,
        event_id=payload.event_id
    )
    return created


@router.get("/cameras", response_model=List[Dict[str, Any]])
@router.get("/api/v1/cameras", response_model=List[Dict[str, Any]])
def get_cameras(user: Dict[str, Any] = Depends(require_operator)):
    """
    TASK 7: Retrieve all cameras with status and live metrics.
    Accessible to: ADMIN + OPERATOR.
    """
    return CameraService.get_cameras()


@router.get("/cameras/{camera_id}", response_model=Dict[str, Any])
@router.get("/api/v1/cameras/{camera_id}", response_model=Dict[str, Any])
def get_camera_detail(camera_id: str, user: Dict[str, Any] = Depends(require_operator)):
    """
    Retrieve single camera by ID.
    Accessible to: ADMIN + OPERATOR.
    """
    cam = CameraService.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found.")
    return cam


@router.put("/cameras/{camera_id}", response_model=Dict[str, Any])
@router.put("/api/v1/cameras/{camera_id}", response_model=Dict[str, Any])
def update_camera(
    camera_id: str,
    payload: CameraUpdateRequest,
    user: Dict[str, Any] = Depends(require_admin)
):
    """
    TASK 7: Update camera configuration or status.
    ADMIN ONLY. OPERATORS receive HTTP 403 Forbidden.
    """
    updates = payload.dict(exclude_unset=True)
    updated = CameraService.update_camera(camera_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found.")
    return updated
