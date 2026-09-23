from fastapi import APIRouter
from typing import List, Dict, Any
from app.database.supabase import get_supabase_client

router = APIRouter(prefix="/api/v1", tags=["Crowd Safety"])


@router.get("/crowd/status")
def get_crowd_status():
    """
    Get current aggregate crowd status across monitored zones.
    If Supabase is connected, reads from crowd_logs.
    Otherwise provides baseline structure.
    """
    client = get_supabase_client()
    if client:
        try:
            res = (
                client.table("crowd_logs")
                .select("*, cameras(camera_name, zone)")
                .order("timestamp", desc=True)
                .limit(10)
                .execute()
            )
            if res.data:
                return {"status": "live", "data": res.data}
        except Exception:
            pass

    # Baseline placeholder data for initial Phase 1 setup
    return {
        "status": "standby",
        "total_people": 1420,
        "current_density": 2.4,  # people per m²
        "risk_level": "MODERATE",
        "risk_score": 0.42,
        "zones": [
            {"zone": "Main Gate", "people_count": 480, "density": 3.2, "risk": "HIGH"},
            {"zone": "Food Court", "people_count": 310, "density": 1.8, "risk": "LOW"},
            {"zone": "Stage Area", "people_count": 520, "density": 3.8, "risk": "CRITICAL"},
            {"zone": "Emergency Exit A", "people_count": 110, "density": 0.9, "risk": "LOW"}
        ]
    }


@router.get("/alerts")
def get_alerts():
    """
    Retrieve active security and crowd hazard alerts.
    """
    client = get_supabase_client()
    if client:
        try:
            res = (
                client.table("alerts")
                .select("*")
                .eq("resolved", False)
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            if res.data:
                return {"status": "live", "alerts": res.data}
        except Exception:
            pass

    return {
        "status": "standby",
        "alerts": [
            {
                "id": "alt-001",
                "zone": "Stage Area",
                "message": "High density threshold exceeded (>3.5 ppl/m²)",
                "severity": "CRITICAL",
                "created_at": "2026-09-23T10:15:00Z",
                "resolved": False
            },
            {
                "id": "alt-002",
                "zone": "Main Gate",
                "message": "Bottleneck detected at entrance turnstiles",
                "severity": "WARNING",
                "created_at": "2026-09-23T10:18:22Z",
                "resolved": False
            }
        ]
    }


@router.get("/events")
def get_events():
    """
    Retrieve registered public events.
    """
    client = get_supabase_client()
    if client:
        try:
            res = client.table("events").select("*").order("date", desc=True).execute()
            if res.data:
                return {"status": "live", "events": res.data}
        except Exception:
            pass

    return {
        "status": "standby",
        "events": [
            {
                "id": "evt-001",
                "event_name": "Metro Music Festival 2026",
                "location": "Central Arena",
                "date": "2026-09-23T18:00:00Z",
                "status": "ACTIVE"
            }
        ]
    }
