"""
PCB Builder - Idempotency Middleware
Ensures mutating operations are idempotent using client-provided keys.
"""

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from shared.database import async_session_factory
from shared.models import IdempotencyKey
from shared.schemas import IdempotencyConflictResponse

IDEMPOTENCY_TTL_SECONDS = 86400  # 24 hours
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces idempotency for mutating requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only enforce for mutating methods
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        key = request.headers.get(IDEMPOTENCY_KEY_HEADER)
        if not key:
            # Idempotency key is optional but recommended
            return await call_next(request)

        # Validate key format (UUID v4 strongly recommended)
        if len(key) > 64:
            raise HTTPException(status_code=400, detail="Idempotency-Key too long (max 64 chars)")

        # Read request body for hash
        body = await request.body()
        request_hash = hashlib.sha256(body).hexdigest()

        async with async_session_factory() as db:
            existing = await db.execute(select(IdempotencyKey).where(IdempotencyKey.key == key))
            record = existing.scalar_one_or_none()

            if record:
                # Duplicate key
                if record.request_hash != request_hash:
                    raise HTTPException(
                        status_code=409,
                        detail=IdempotencyConflictResponse(
                            message="Idempotency key was used with different request body",
                            details=f"Request hash mismatch: expected {record.request_hash[:16]}...",
                        ).model_dump_json(),
                    )
                # Return stored response
                response = Response(
                    content=json.dumps(record.response_body),
                    status_code=record.response_status,
                    media_type="application/json",
                )
                response.headers["Idempotency-Key"] = key
                return response

        # No existing record - proceed and store response
        response = await call_next(request)

        # Only store successful responses
        if 200 <= response.status_code < 300:
            try:
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk

                body_json = json.loads(response_body.decode("utf-8"))
                expires = datetime.now(timezone.utc) + timedelta(seconds=IDEMPOTENCY_TTL_SECONDS)

                async with async_session_factory() as db:
                    record = IdempotencyKey(
                        key=key,
                        request_hash=request_hash,
                        response_status=response.status_code,
                        response_body=body_json,
                        expires_at=expires,
                    )
                    db.add(record)
                    await db.commit()

                # Reconstruct response
                response = Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type="application/json",
                )
                response.headers["Idempotency-Key"] = key
            except Exception:
                pass  # Don't fail the request if caching fails

        return response
