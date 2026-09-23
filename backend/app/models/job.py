from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.QUEUED


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = 0
    current_count: Optional[int] = 0
    current_frame: Optional[int] = 0
    total_frames: Optional[int] = 0
    boxes: Optional[List[Any]] = []
    message: Optional[str] = None


class JobResultResponse(BaseModel):
    job_id: str
    status: JobStatus
    people_count: int
    average_people: Optional[int] = None
    max_people: Optional[int] = None
    total_frames: Optional[int] = None
    duration: Optional[int] = None
    camera_id: Optional[str] = None
    supabase_logged: bool = False
    sample_frames: Optional[List[Any]] = []
    initial_boxes: Optional[List[Any]] = []
    error: Optional[str] = None
