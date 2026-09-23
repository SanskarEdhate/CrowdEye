import logging
from typing import Optional, Dict, Any
from supabase import create_client, Client
from app.config.settings import settings

logger = logging.getLogger("crowdeye.database")

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """
    Returns a reusable Supabase client instance.
    Uses SUPABASE_URL and SUPABASE_SERVICE_KEY from environment.
    Returns None with a warning if credentials are not configured.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not settings.is_supabase_configured:
        logger.warning(
            "Supabase credentials not configured or incomplete. "
            "Please configure SUPABASE_URL and SUPABASE_SERVICE_KEY in backend/.env."
        )
        return None

    try:
        _supabase_client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_SERVICE_KEY
        )
        logger.info("Supabase client initialized successfully with service role key.")
        return _supabase_client
    except Exception as exc:
        logger.error(f"Failed to initialize Supabase client: {exc}")
        return None


def check_supabase_connection() -> Dict[str, Any]:
    """
    Tests connectivity to Supabase.
    Returns a structured status dictionary.
    """
    if not settings.is_supabase_configured:
        return {
            "connected": False,
            "status": "unconfigured",
            "message": "SUPABASE_URL or SUPABASE_SERVICE_KEY missing in .env",
            "url_configured": bool(settings.SUPABASE_URL),
            "key_configured": bool(settings.SUPABASE_SERVICE_KEY),
        }

    client = get_supabase_client()
    if client is None:
        return {
            "connected": False,
            "status": "initialization_failed",
            "message": "Could not instantiate Supabase client with provided credentials",
        }

    try:
        # Lightweight check: Query events table limit 1
        response = client.table("events").select("id").limit(1).execute()
        return {
            "connected": True,
            "status": "connected",
            "message": "Successfully connected to Supabase database",
            "details": f"Query response received: {len(response.data)} records",
        }
    except Exception as exc:
        # Check if error is just table not created yet or network/auth error
        error_msg = str(exc)
        return {
            "connected": False,
            "status": "error",
            "message": f"Connection check encountered error: {error_msg}",
        }
