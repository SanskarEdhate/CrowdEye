from fastapi import APIRouter
from app.config.settings import settings
from app.database.supabase import check_supabase_connection

router = APIRouter(prefix="/api/v1", tags=["Health & Status"])


@router.get("/health")
def get_system_health():
    """Health status of backend service"""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "healthy"
    }


@router.get("/supabase-test")
def test_supabase():
    """Test connectivity to Supabase backend service"""
    return check_supabase_connection()
