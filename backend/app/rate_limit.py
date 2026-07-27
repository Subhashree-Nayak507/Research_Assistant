"""
Basic rate limiting.

Why per-endpoint different limits:
- /auth/login and /auth/register are brute-force / spam targets -> tight limit
- /research/ws is expensive (calls LLMs) -> tight limit per user
- everything else -> a generous default so normal use never gets blocked

In-memory storage is fine for a single-process demo. If you run more than
one backend worker/replica, point `storage_uri` at Redis instead so all
workers share the same counters:
    storage_uri=settings.REDIS_URL
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,  # rate-limit by client IP
    default_limits=["60/minute"],
    # Use Redis only if a real REDIS_URL was actually configured — this
    # can never crash from a missing setting, unlike checking
    # ENVIRONMENT == "production" and assuming Redis exists because of it.
    storage_uri=settings.REDIS_URL or "memory://",
)