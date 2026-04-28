"""
PCB Builder - Correlation ID Middleware
Injects and propagates correlation IDs across all requests.
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns or forwards correlation IDs."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Accept existing correlation ID from client or generate new one
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        _correlation_id.set(cid)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response


def get_correlation_id() -> str:
    """Get current request correlation ID."""
    return _correlation_id.get() or "unknown"
