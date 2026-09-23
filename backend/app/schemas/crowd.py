from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    name: str
    email: str
    role: str = "security"


class EventBase(BaseModel):
    event_name: str
    location: str
    date: datetime
    status: str = "SCHEDULED"


class CameraBase(BaseModel):
    event_id: UUID
    camera_name: str
    zone: str
    stream_url: Optional[str] = None


class CrowdLogCreate(BaseModel):
    camera_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    people_count: int
    density: float
    risk_score: float
    status: str


class AlertCreate(BaseModel):
    event_id: UUID
    zone: str
    message: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    resolved: bool = False
