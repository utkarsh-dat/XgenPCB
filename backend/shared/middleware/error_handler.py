"""
PCB Builder - Structured Error Handler
Converts all exceptions into consistent JSON error responses.
"""

import traceback
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from shared.logging_config import logger
from shared.middleware.correlation import get_correlation_id


class APIError(Exception):
    """Base class for structured API errors."""

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 500,
        details: Any = None,
        suggestion: str = "",
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.suggestion = suggestion
        super().__init__(message)


def build_error_response(
    error_code: str,
    message: str,
    status_code: int = 500,
    details: Any = None,
    suggestion: str = "",
    exc: Exception | None = None,
) -> JSONResponse:
    """Build a consistent JSON error response."""
    payload = {
        "error_code": error_code,
        "message": message,
        "details": details,
        "suggestion": suggestion,
        "correlation_id": get_correlation_id(),
    }
    if exc and hasattr(exc, "__traceback__"):
        payload["trace_id"] = str(id(exc))

    return JSONResponse(status_code=status_code, content=payload)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle FastAPI/Starlette HTTP exceptions."""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
    )

    if isinstance(exc.detail, dict):
        return build_error_response(
            error_code=exc.detail.get("error_code", f"HTTP_{exc.status_code}"),
            message=exc.detail.get("message", str(exc.detail)),
            status_code=exc.status_code,
            details=exc.detail.get("details"),
            suggestion=exc.detail.get("suggestion", ""),
        )

    return build_error_response(
        error_code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        status_code=exc.status_code,
        suggestion="Check your request and try again.",
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error.get("loc", []))
        details.append({
            "field": field,
            "issue": error.get("msg", ""),
            "constraint": error.get("type", ""),
            "suggestion": "Ensure the field matches the expected format and constraints.",
        })

    logger.warning(
        "Validation error",
        path=request.url.path,
        method=request.method,
        errors_count=len(details),
    )

    return build_error_response(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=422,
        details=details,
        suggestion="Review and correct the listed fields before resubmitting.",
    )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle custom APIError exceptions."""
    logger.error(
        "API error",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
    )
    return build_error_response(
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        suggestion=exc.suggestion,
        exc=exc,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        "Unhandled exception",
        exc_info=True,
        path=request.url.path,
        method=request.method,
        correlation_id=get_correlation_id(),
    )
    return build_error_response(
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        status_code=500,
        suggestion="Please try again later. If the issue persists, contact support.",
        exc=exc,
    )
