import logging
from typing import List, Optional, Dict, Any
from fastapi import Request, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database.supabase import get_supabase_client

logger = logging.getLogger("crowdeye.auth.security")

# Optional HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Dict[str, Any]:
    """
    Extracts authenticated user and role.
    Supports:
    1. Authorization Bearer JWT (Supabase Auth & profiles table)
    2. Header 'X-User-Role' or 'X-Role' for direct operator/admin toggle & testing
    3. Query parameter '?role=ADMIN' or '?role=OPERATOR'
    Defaults to 'OPERATOR' if unauthenticated.
    """
    # 1. Direct header or query parameter override (crucial for local testing & control room role switcher)
    explicit_role = (
        request.headers.get("X-User-Role")
        or request.headers.get("X-Role")
        or request.query_params.get("role")
    )
    if explicit_role:
        role_clean = explicit_role.strip().upper()
        if role_clean in ("ADMIN", "OPERATOR"):
            return {
                "id": "operator-local-session",
                "role": role_clean,
                "email": f"{role_clean.lower()}@crowdeye.ai"
            }

    # 2. Check Supabase Auth Bearer token if provided
    token = credentials.credentials if credentials else None
    if token:
        client = get_supabase_client()
        if client:
            try:
                user_res = client.auth.get_user(token)
                if user_res and user_res.user:
                    user_id = user_res.user.id
                    user_email = user_res.user.email

                    # Query profiles table for role
                    role = "OPERATOR"
                    try:
                        p_res = client.table("profiles").select("role").eq("id", user_id).limit(1).execute()
                        if p_res.data and len(p_res.data) > 0:
                            role = p_res.data[0].get("role", "OPERATOR")
                    except Exception as e:
                        logger.debug(f"Profiles query fallback: {e}")

                    return {
                        "id": user_id,
                        "role": role.upper(),
                        "email": user_email
                    }
            except Exception as e:
                logger.debug(f"Supabase auth validation error: {e}")

    # 3. Default fallback role: OPERATOR (permits read & resolve, blocks admin mutations)
    return {
        "id": "default-operator-id",
        "role": "OPERATOR",
        "email": "operator@crowdeye.ai"
    }


def require_role(allowed_roles: List[str]):
    """
    Dependency factory that enforces Role-Based Access Control (RBAC).
    Raises HTTP 403 Forbidden if user's role is not within allowed_roles.
    """
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = user.get("role", "OPERATOR").upper()
        if user_role not in [r.upper() for r in allowed_roles]:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: Action requires one of {allowed_roles} role(s). Your role is '{user_role}'."
            )
        return user
    return role_checker


# Convenient dependencies
require_admin = require_role(["ADMIN"])
require_operator = require_role(["ADMIN", "OPERATOR"])
