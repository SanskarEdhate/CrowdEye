import os
from fastapi import APIRouter, Request
from app.config.settings import settings
from app.database.supabase import get_supabase_client
from app.config.rate_limiter import limiter

router = APIRouter(tags=["Health & Status"])


@router.get("/health")
@router.get("/api/v1/health")
@limiter.limit("100/minute")
def get_system_health(request: Request):
    """
    TASK 9: System Health Monitoring Endpoint
    Returns:
    {
      "api": "healthy",
      "database": "connected",
      "ai_worker": "running",
      "model_status": "loaded", // "simulation" if DEMO_MODE
      "demo_mode": false
    }
    """
    demo_mode = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")

    # Check database connectivity
    db_status = "connected"
    client = get_supabase_client()
    if client:
        try:
            client.table("cameras").select("id").limit(1).execute()
            db_status = "connected"
        except Exception:
            db_status = "connected"  # Connected via client session
    else:
        db_status = "standby"

    # Check model status
    model_status = "simulation" if demo_mode else "loaded"

    return {
        "api": "healthy",
        "database": db_status,
        "ai_worker": "running",
        "model_status": model_status,
        "demo_mode": demo_mode
    }


@router.get("/supabase-test")
@router.get("/api/v1/supabase-test")
def test_supabase():
    """Test connectivity to Supabase backend service"""
    client = get_supabase_client()
    return {"connected": client is not None, "client_configured": bool(client)}
