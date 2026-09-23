import os
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_KEY", "crowdeye-internal-ai-worker-token-2026")


def rate_limit_key_func(request: Request) -> str:
    """
    TASK 8 Rate Limiter Key Strategy:
    - Internal AI pipeline: exempt with service key.
    - Authenticated users: rate-limited by user token/ID.
    - Public APIs: rate-limited by client IP.
    """
    # 1. Exempt internal AI Worker pipeline
    internal_token = request.headers.get("X-Service-Key") or request.headers.get("X-Internal-Token")
    if internal_token and internal_token == INTERNAL_SERVICE_SECRET:
        return "exempt_internal_service"

    # 2. Authenticated user key
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        # Return first 30 chars of token as unique user rate-limit key
        return f"user_{token[:32]}"

    user_role_header = request.headers.get("X-User-Role")
    if user_role_header:
        client_ip = get_remote_address(request)
        return f"user_{user_role_header}_{client_ip}"

    # 3. Public IP key
    return f"ip_{get_remote_address(request)}"


limiter = Limiter(
    key_func=rate_limit_key_func,
    default_limits=["100/minute"]
)
