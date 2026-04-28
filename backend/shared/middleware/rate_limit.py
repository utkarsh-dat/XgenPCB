"""
PCB Builder - Rate Limiting Middleware
Tiered rate limiting: Free, Pro, Enterprise.
"""

import time
from typing import Optional

from fastapi import HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from shared.config import get_settings
from shared.middleware.auth import get_optional_user

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    strategy="fixed-window",
)


def get_rate_limit_for_user(user) -> str:
    """Return rate limit string based on user tier."""
    if not user:
        return "10/minute"
    tier = user.subscription_tier or "free"
    limits = {
        "free": "10/minute",
        "pro": "60/minute",
        "enterprise": "300/minute",
    }
    return limits.get(tier, "10/minute")


async def rate_limit_dependency(request: Request):
    """Dependency to apply dynamic rate limits."""
    # This is a placeholder; actual enforcement is done via slowapi decorators
    pass
